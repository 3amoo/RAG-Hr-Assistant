from controllers import NLPController
from stores.vectordb.VectorDBEnums import PgVectorTableSchemeEnums

from fakes import FakeVectorDB


def test_collection_name_uses_vectors_prefix():
    controller = NLPController(FakeVectorDB([]), None, None, None)
    assert controller.create_collection_name(7) == "vectors_1024_7"


def test_pgvector_table_prefix_matches_collection_prefix():
    assert PgVectorTableSchemeEnums._PREFIX.value == "vectors_"
