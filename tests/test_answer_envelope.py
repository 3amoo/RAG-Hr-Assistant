import pytest

from controllers import NLPController
from stores.llm.templates.template_parser import TemplateParser

from fakes import (
    FakeEmbedding,
    FakeGeneration,
    FakeProject,
    FakeVectorDB,
    document,
)


def make_controller(documents, answer="Here is the answer."):
    return NLPController(
        vectordb_client=FakeVectorDB(documents),
        generation_client=FakeGeneration(answer),
        embedding_client=FakeEmbedding(),
        template_parser=TemplateParser(language="en", default_language="en"),
    )


@pytest.mark.asyncio
async def test_answer_has_citations_and_is_not_low_confidence():
    documents = [
        document(
            "Annual leave is 25 days.",
            0.8,
            chunk_id=7,
            metadata={"source": "leave-policy.txt", "page": 2, "doc_type": "POLICY"},
        )
    ]
    result = await make_controller(documents).answer_rag_question(
        FakeProject(), "How many leave days?"
    )

    assert result.answer == "Here is the answer."
    assert result.low_confidence is False
    assert len(result.citations) == 1
    citation = result.citations[0]
    assert citation.chunk_id == 7
    assert citation.asset_name == "leave-policy.txt"
    assert citation.page == 2
    assert citation.doc_type == "POLICY"
    assert citation.score == 0.8
    assert citation.quote == "Annual leave is 25 days."


@pytest.mark.asyncio
async def test_below_threshold_is_refused_without_citations():
    documents = [document("Weak match.", 0.1)]
    result = await make_controller(documents).answer_rag_question(
        FakeProject(), "Unrelated question?"
    )

    assert result.low_confidence is True
    assert result.citations == []
    assert "enough relevant information" in result.answer


@pytest.mark.asyncio
async def test_no_retrieval_is_refused():
    result = await make_controller([]).answer_rag_question(
        FakeProject(), "Anything?"
    )

    assert result.low_confidence is True
    assert result.citations == []


@pytest.mark.asyncio
async def test_generation_failure_is_refused():
    result = await make_controller(
        [document("Relevant text.", 0.9)], answer=""
    ).answer_rag_question(FakeProject(), "Question?")

    assert result.low_confidence is True
    assert result.citations == []
