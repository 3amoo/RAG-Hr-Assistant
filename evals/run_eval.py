#!/usr/bin/env python3
"""Offline evaluation for the policy copilot.

No API calls, no database and no LLM judge. Retrieval is a deterministic
lexical scorer over the synthetic documents from scripts/generate_sample_data.
Reports hit@5, citation validity and refusal accuracy.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

os.environ.update(
    {
        "APP_NAME": "RAG-Hr-Assistant",
        "APP_VERSION": "eval",
        "FILE_ALLOWED_TYPES": '["text/plain", "application/pdf"]',
        "FILE_MAX_SIZE": "10",
        "FILE_DEFAULT_CHUNK_SIZE": "1000",
        "POSTGRES_USERNAME": "test",
        "POSTGRES_PASSWORD": "test",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_MAIN_DATABASE": "test",
        "GENERATION_BACKEND": "OPENAI",
        "EMBEDDING_BACKEND": "COHERE",
        "VECTOR_DB_BACKEND": "PGVECTOR",
        "VECTOR_DB_PATH": "qdrant_db",
        "PRIMARY_LANG": "en",
        "DEFAULT_LANG": "en",
        "API_KEY": "",
    }
)

from controllers import NLPController  # noqa: E402
from helpers.config import get_settings  # noqa: E402
from models.db_schemes import RetrievedDocument  # noqa: E402
from scripts.generate_sample_data import DOCUMENTS  # noqa: E402
from stores.llm.templates.template_parser import TemplateParser  # noqa: E402

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does",
    "for", "from", "how", "in", "is", "it", "many", "max", "maximum", "much",
    "of", "on", "or", "should", "that", "the", "their", "to", "what", "when",
    "where", "which", "who", "with", "within", "ما", "هي", "هل", "عن", "في",
    "من", "على", "إلى", "بشأن", "كم", "كيف",
}


def tokenize(text: str) -> set[str]:
    return {word for word in re.findall(r"\w+", text.lower()) if word not in STOPWORDS}


def build_idf(corpus_tokens: list[set[str]]) -> dict[str, float]:
    document_count = len(corpus_tokens)
    frequencies: Counter[str] = Counter()
    for tokens in corpus_tokens:
        frequencies.update(tokens)
    return {
        token: math.log(document_count / frequency)
        for token, frequency in frequencies.items()
    }


def lexical_score(query_tokens: set[str], doc_tokens: set[str], idf: dict[str, float]) -> float:
    if not query_tokens:
        return 0.0
    total = sum(idf.get(token, math.log(len(CORPUS) + 1)) for token in query_tokens)
    matched = sum(idf.get(token, 0.0) for token in query_tokens & doc_tokens)
    return matched / total if total else 0.0


class FakeEmbedding:
    embedding_size = 1024

    def __init__(self, state):
        self.state = state

    def embed_text(self, text, document_type=None):
        texts = text if isinstance(text, list) else [text]
        self.state["query"] = texts[0]
        return [[0.1] * self.embedding_size for _ in texts]


class FakeGeneration:
    class enums:
        SYSTEM = type("SystemRole", (), {"value": "system"})()

    def process_text(self, text):
        return text

    def construct_prompt(self, prompt, role):
        return {"role": role, "content": prompt}

    def generate_text(self, prompt, chat_history=None):
        return "Based on the indexed policy, here is the answer."


class LexicalVectorDB:
    default_vector_size = 1024

    def __init__(self, state, corpus, corpus_tokens, idf):
        self.state = state
        self.corpus = corpus
        self.corpus_tokens = corpus_tokens
        self.idf = idf

    async def search_by_vector(self, collection_name, vector, limit):
        query_tokens = tokenize(self.state["query"])
        scored = [
            (lexical_score(query_tokens, tokens, self.idf), index)
            for index, tokens in enumerate(self.corpus_tokens)
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            RetrievedDocument(
                text=self.corpus[index][1],
                score=score,
                chunk_id=index + 1,
                metadata={
                    "source": self.corpus[index][0],
                    "page": 1,
                    "doc_type": "POLICY",
                },
            )
            for score, index in scored[:limit]
        ]


class FakeProject:
    project_id = 1


CORPUS = [(name, text) for name, text in DOCUMENTS.items()]
CORPUS_TOKENS = [tokenize(text) for _, text in CORPUS]
IDF = build_idf(CORPUS_TOKENS)
SOURCE_TEXT = dict(CORPUS)


def percentage(values: list[bool]) -> float:
    return 100.0 * sum(values) / len(values) if values else 0.0


def main() -> int:
    golden = json.loads((ROOT / "evals" / "golden.json").read_text(encoding="utf-8"))
    settings = get_settings()

    state = {"query": ""}
    controller = NLPController(
        vectordb_client=LexicalVectorDB(state, CORPUS, CORPUS_TOKENS, IDF),
        generation_client=FakeGeneration(),
        embedding_client=FakeEmbedding(state),
        template_parser=TemplateParser(
            language=settings.PRIMARY_LANG, default_language=settings.DEFAULT_LANG
        ),
    )

    hits: list[bool] = []
    refusals: list[bool] = []
    citation_checks: list[bool] = []

    for item in golden:
        state["query"] = ""
        result = asyncio.run(
            controller.answer_rag_question(
                project=FakeProject(), query=item["question"], limit=5
            )
        )
        refusals.append(result.low_confidence == item["expected_refusal"])

        if not result.low_confidence and item["expected_source"]:
            hits.append(
                item["expected_source"]
                in [citation.asset_name for citation in result.citations]
            )

        for citation in result.citations:
            source = SOURCE_TEXT.get(citation.asset_name or "", "")
            citation_checks.append(
                bool(source)
                and bool(citation.quote)
                and citation.quote in source
                and citation.score >= settings.MIN_RETRIEVAL_SCORE
            )

    metrics = {
        "hit@5": (percentage(hits), 80.0, len(hits)),
        "citation validity": (percentage(citation_checks), 100.0, len(citation_checks)),
        "refusal accuracy": (percentage(refusals), 90.0, len(refusals)),
    }

    print(f"Golden questions: {len(golden)}")
    for name, (value, threshold, count) in metrics.items():
        status = "PASS" if value >= threshold else "FAIL"
        print(f"{name:20s} {value:6.1f}%  (threshold {threshold:.0f}%, n={count})  {status}")

    return 0 if all(value >= threshold for value, threshold, _ in metrics.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
