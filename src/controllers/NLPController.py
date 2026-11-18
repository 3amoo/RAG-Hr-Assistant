# ======================================================
# Import Libs
# ======================================================

from .BaseController import BaseController
from models.db_schemes import Project, DataChunk, RetrievedDocument
from models.RagModels import Citation, RagAnswer
from stores.llm.LLMEnums import DocumentTypeEnum
from typing import List
import json


# ======================================================
# Func.
# ======================================================
# - NLPController — orchestrate indexing, retrieval and RAG answers
#   - __init__ — initialize instance state and dependencies
#   - create_collection_name — build the size/project-specific collection name
#   - reset_vector_db_collection — delete and recreate a project collection
#   - get_vector_db_collection_info — return collection statistics or None
#   - index_into_vector_db — embed chunks and insert them into the vector store
#   - search_vector_db_collection — run vector similarity search for a query
#   - _build_citation — build a citation object from a retrieved chunk
#   - _refusal — return the standard low-confidence refusal
#   - answer_rag_question — retrieve evidence and generate a cited answer
# ======================================================

class NLPController(BaseController):

    def __init__(self, vectordb_client, generation_client, 
                 embedding_client, template_parser):
        super().__init__()

        self.vectordb_client = vectordb_client
        self.generation_client = generation_client
        self.embedding_client = embedding_client
        self.template_parser = template_parser

    def create_collection_name(self, project_id: str):
        return f"vectors_{self.vectordb_client.default_vector_size}_{project_id}".strip()
    
    async def reset_vector_db_collection(self, project: Project):
        collection_name = self.create_collection_name(project_id=project.project_id)
        return await self.vectordb_client.delete_collection(collection_name=collection_name)
    
    async def get_vector_db_collection_info(self, project: Project):
        collection_name = self.create_collection_name(project_id=project.project_id)
        collection_info = await self.vectordb_client.get_collection_info(collection_name=collection_name)

        return json.loads(
            json.dumps(collection_info, default=lambda x: x.__dict__)
        )
    
    async def index_into_vector_db(self, project: Project, chunks: List[DataChunk],
                                   chunks_ids: List[int], 
                                   do_reset: bool = False):
        
        # step1: get collection name
        collection_name = self.create_collection_name(project_id=project.project_id)

        # step2: manage items
        texts = [ c.chunk_text for c in chunks ]
        metadata = [ c.chunk_metadata for c in  chunks]
        vectors = self.embedding_client.embed_text(text=texts, 
                                                  document_type=DocumentTypeEnum.DOCUMENT.value)

        if not vectors:
            return False

        # step3: create collection if not exists
        _ = await self.vectordb_client.create_collection(
            collection_name=collection_name,
            embedding_size=self.embedding_client.embedding_size,
            do_reset=do_reset,
        )

        # step4: insert into vector db
        inserted = await self.vectordb_client.insert_many(
            collection_name=collection_name,
            texts=texts,
            metadata=metadata,
            vectors=vectors,
            record_ids=chunks_ids,
        )

        return bool(inserted)

    async def search_vector_db_collection(self, project: Project, text: str, limit: int = 10):

        # step1: get collection name
        query_vector = None
        collection_name = self.create_collection_name(project_id=project.project_id)

        # step2: get text embedding vector
        vectors = self.embedding_client.embed_text(text=text, 
                                                 document_type=DocumentTypeEnum.QUERY.value)

        if not vectors or len(vectors) == 0:
            return False
        
        if isinstance(vectors, list) and len(vectors) > 0:
            query_vector = vectors[0]

        if not query_vector:
            return False    

        # step3: do semantic search
        results = await self.vectordb_client.search_by_vector(
            collection_name=collection_name,
            vector=query_vector,
            limit=limit
        )

        if not results:
            return False

        return results
    
    QUOTE_MAX_CHARS = 240

    def _build_citation(self, document: RetrievedDocument) -> Citation:
        metadata = document.metadata or {}
        return Citation(
            chunk_id=document.chunk_id,
            asset_name=metadata.get("source"),
            doc_type=metadata.get("doc_type"),
            page=metadata.get("page"),
            section=metadata.get("section"),
            score=float(document.score),
            quote=document.text[: self.QUOTE_MAX_CHARS],
        )

    def _refusal(self) -> RagAnswer:
        return RagAnswer(
            answer=self.template_parser.get("rag", "refusal_message"),
            citations=[],
            low_confidence=True,
        )

    async def answer_rag_question(self, project: Project, query: str, limit: int = 10):
        # step1: retrieve related documents
        retrieved_documents = await self.search_vector_db_collection(
            project=project,
            text=query,
            limit=limit,
        )

        if not retrieved_documents:
            return self._refusal()

        # step2: refuse when no retrieval clears the confidence threshold
        threshold = self.app_settings.MIN_RETRIEVAL_SCORE
        relevant_documents = [
            doc for doc in retrieved_documents if float(doc.score) >= threshold
        ]

        if not relevant_documents:
            return self._refusal()

        # step3: construct the LLM prompt from the relevant documents
        system_prompt = self.template_parser.get("rag", "system_prompt")

        documents_prompts = "\n".join([
            self.template_parser.get("rag", "document_prompt", {
                    "doc_num": idx + 1,
                    "chunk_text": self.generation_client.process_text(doc.text),
            })
            for idx, doc in enumerate(relevant_documents)
        ])

        footer_prompt = self.template_parser.get("rag", "footer_prompt", {
            "query": query
        })

        chat_history = [
            self.generation_client.construct_prompt(
                prompt=system_prompt,
                role=self.generation_client.enums.SYSTEM.value,
            )
        ]

        full_prompt = "\n\n".join([ documents_prompts, footer_prompt ])

        answer = self.generation_client.generate_text(
            prompt=full_prompt,
            chat_history=chat_history
        )

        if not answer:
            return self._refusal()

        return RagAnswer(
            answer=answer,
            citations=[self._build_citation(doc) for doc in relevant_documents],
            low_confidence=False,
        )

