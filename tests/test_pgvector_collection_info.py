import pytest

from stores.vectordb.providers.PGVectorProvider import PGVectorProvider


class _Result:
    def __init__(self, row=None, count=0):
        self._row = row
        self._count = count

    def fetchone(self):
        return self._row

    def scalar_one(self):
        return self._count


class _Session:
    """Fake session that fails loudly if COUNT runs for a missing collection."""

    def __init__(self, table_exists):
        self.table_exists = table_exists
        self.executed = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def begin(self):
        return self

    async def execute(self, sql, params=None):
        statement = str(sql)
        self.executed.append(statement)
        if "pg_tables" in statement:
            row = None
            if self.table_exists:
                row = ("public", "vectors_1024_1", "postgres", None, False)
            return _Result(row=row)
        if "COUNT" in statement:
            if not self.table_exists:
                raise AssertionError("COUNT(*) ran for a missing collection")
            return _Result(count=5)
        raise AssertionError(f"Unexpected SQL: {statement}")


class _DbClient:
    def __init__(self, session):
        self.session = session

    def __call__(self):
        return self.session


@pytest.mark.asyncio
async def test_missing_collection_returns_none_without_counting_rows():
    session = _Session(table_exists=False)
    provider = PGVectorProvider(db_client=_DbClient(session))

    result = await provider.get_collection_info("vectors_1024_1")

    assert result is None
    # Only the table-info lookup should have run; COUNT(*) must be skipped.
    assert len(session.executed) == 1


@pytest.mark.asyncio
async def test_existing_collection_returns_info_and_count():
    session = _Session(table_exists=True)
    provider = PGVectorProvider(db_client=_DbClient(session))

    result = await provider.get_collection_info("vectors_1024_1")

    assert result["record_count"] == 5
    assert result["table_info"]["tablename"] == "vectors_1024_1"
    assert result["table_info"]["schemaname"] == "public"
    assert len(session.executed) == 2
