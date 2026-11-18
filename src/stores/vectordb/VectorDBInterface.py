# ======================================================
# Import Libs
# ======================================================

from abc import ABC, abstractmethod
from typing import List
from models.db_schemes import RetrievedDocument


# ======================================================
# Func.
# ======================================================
# - VectorDBInterface — abstract contract for vector stores
#   - connect — open the vector store connection
#   - disconnect — close the vector store connection
#   - is_collection_existed — check whether a collection exists
#   - list_all_collections — list available collections
#   - get_collection_info — handle get collection info
#   - delete_collection — drop a collection
#   - create_collection — create a collection with the configured distance
#   - insert_one — insert a single vector record
#   - insert_many — bulk insert vector records
#   - search_by_vector — query the collection by vector similarity
# ======================================================

class VectorDBInterface(ABC):

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def is_collection_existed(self, collection_name: str) -> bool:
        pass

    @abstractmethod
    def list_all_collections(self) -> List:
        pass

    @abstractmethod
    def get_collection_info(self, collection_name: str) -> dict:
        pass

    @abstractmethod
    def delete_collection(self, collection_name: str):
        pass

    @abstractmethod
    def create_collection(self, collection_name: str, 
                                embedding_size: int,
                                do_reset: bool = False):
        pass

    @abstractmethod
    def insert_one(self, collection_name: str, text: str, vector: list,
                         metadata: dict = None, 
                         record_id: str = None):
        pass

    @abstractmethod
    def insert_many(self, collection_name: str, texts: list, 
                          vectors: list, metadata: list = None, 
                          record_ids: list = None, batch_size: int = 50):
        pass

    @abstractmethod
    def search_by_vector(self, collection_name: str, vector: list, limit: int) -> List[RetrievedDocument]:
        pass
    