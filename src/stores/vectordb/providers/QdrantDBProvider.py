import logging
from typing import List

from qdrant_client import QdrantClient, models

from models.db_schemes import RetrievedDocument

from ..VectorDBEnums import DistanceMethodEnums
from ..VectorDBInterface import VectorDBInterface


class QdrantDBProvider(VectorDBInterface):

    def __init__(self, db_client: str = None, default_vector_size: int = 786,
                 distance_method: str = None, index_threshold: int = 100,
                 url: str = None, api_key: str = None):

        self.client = None
        self.db_client = db_client
        self.url = url or None
        self.api_key = api_key or None
        self.distance_method = models.Distance.COSINE
        self.default_vector_size = default_vector_size
        self.index_threshold = index_threshold

        if distance_method == DistanceMethodEnums.DOT.value:
            self.distance_method = models.Distance.DOT

        self.logger = logging.getLogger("uvicorn")

    async def connect(self):
        if self.url:
            self.client = QdrantClient(url=self.url, api_key=self.api_key)
        else:
            self.client = QdrantClient(path=self.db_client)

    async def disconnect(self):
        if self.client is not None:
            self.client.close()
        self.client = None

    async def is_collection_existed(self, collection_name: str) -> bool:
        return self.client.collection_exists(collection_name=collection_name)

    async def list_all_collections(self) -> List:
        return self.client.get_collections().collections

    async def get_collection_info(self, collection_name: str) -> dict:
        return self.client.get_collection(collection_name=collection_name)

    async def delete_collection(self, collection_name: str):
        if await self.is_collection_existed(collection_name):
            self.logger.info("Deleting collection: %s", collection_name)
            return self.client.delete_collection(collection_name=collection_name)

        return False

    async def create_collection(self, collection_name: str,
                                embedding_size: int,
                                do_reset: bool = False):
        if do_reset:
            _ = await self.delete_collection(collection_name=collection_name)

        if not await self.is_collection_existed(collection_name):
            self.logger.info("Creating new Qdrant collection: %s", collection_name)
            _ = self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=embedding_size,
                    distance=self.distance_method,
                ),
            )
            return True

        return False

    async def insert_one(self, collection_name: str, text: str, vector: list,
                         metadata: dict = None, record_id: str = None):
        if not await self.is_collection_existed(collection_name):
            self.logger.error(
                "Can not insert new record to non-existed collection: %s",
                collection_name,
            )
            return False

        if record_id is None:
            self.logger.error("Can not insert a record without an id")
            return False

        try:
            _ = self.client.upsert(
                collection_name=collection_name,
                points=[
                    models.PointStruct(
                        id=record_id,
                        vector=vector,
                        payload={"text": text, "metadata": metadata or {}},
                    )
                ],
            )
        except Exception as e:
            self.logger.error("Error while inserting record: %s", e)
            return False

        return True

    async def insert_many(self, collection_name: str, texts: list,
                          vectors: list, metadata: list = None,
                          record_ids: list = None, batch_size: int = 50):
        if not await self.is_collection_existed(collection_name):
            self.logger.error(
                "Can not insert new records to non-existed collection: %s",
                collection_name,
            )
            return False

        if metadata is None:
            metadata = [None] * len(texts)

        if record_ids is None:
            record_ids = list(range(0, len(texts)))

        for i in range(0, len(texts), batch_size):
            batch_end = i + batch_size
            batch_texts = texts[i:batch_end]
            batch_vectors = vectors[i:batch_end]
            batch_metadata = metadata[i:batch_end]
            batch_record_ids = record_ids[i:batch_end]

            batch_records = [
                models.PointStruct(
                    id=batch_record_ids[x],
                    vector=batch_vectors[x],
                    payload={
                        "text": batch_texts[x],
                        "metadata": batch_metadata[x] or {},
                    },
                )
                for x in range(len(batch_texts))
            ]

            try:
                _ = self.client.upsert(
                    collection_name=collection_name,
                    points=batch_records,
                )
            except Exception as e:
                self.logger.error("Error while inserting batch: %s", e)
                return False

        return True

    async def search_by_vector(self, collection_name: str, vector: list, limit: int = 5):
        if not await self.is_collection_existed(collection_name):
            self.logger.error(
                "Can not search for records in a non-existed collection: %s",
                collection_name,
            )
            return None

        results = self.client.search(
            collection_name=collection_name,
            query_vector=vector,
            limit=limit,
        )

        if not results:
            return None

        return [
            RetrievedDocument(
                score=result.score,
                text=result.payload.get("text", ""),
            )
            for result in results
        ]
