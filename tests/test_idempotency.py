from datetime import datetime, timedelta, timezone

import pytest

from utils.idempotency_manager import IdempotencyManager


class _Result:
    def __init__(self, record=None):
        self._record = record

    def scalar_one_or_none(self):
        return self._record


class _Session:
    """Fake session returning scripted results in execute() call order."""

    def __init__(self, results):
        self.results = list(results)
        self.commits = 0
        self.rollbacks = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def execute(self, stmt):
        if not self.results:
            raise AssertionError("Unexpected extra execute() call")
        return self.results.pop(0)

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


class _DbClient:
    def __init__(self, session):
        self.session = session

    def __call__(self):
        return self.session


class _Record:
    def __init__(self, status, started_at=None, created_at=None,
                 result=None, execution_id=1):
        self.status = status
        self.started_at = started_at
        self.created_at = created_at or datetime.now(timezone.utc)
        self.result = result
        self.execution_id = execution_id


def _manager(session):
    return IdempotencyManager(db_client=_DbClient(session), db_engine=None)


def _now():
    return datetime.now(timezone.utc)


TASK_NAME = "tasks.file_processing.process_project_files"
TASK_ARGS = {"project_id": 1, "file_id": "policy.txt"}


@pytest.mark.asyncio
async def test_claim_inserts_when_no_prior_execution():
    record = _Record("PENDING")
    session = _Session([_Result(record)])

    result, claimed = await _manager(session).claim_task(TASK_NAME, TASK_ARGS)

    assert claimed is True
    assert result is record
    assert session.commits == 1
    assert session.rollbacks == 0


@pytest.mark.asyncio
async def test_claim_skips_when_existing_task_succeeded():
    existing = _Record("SUCCESS", result={"inserted_chunks": 7})
    session = _Session([_Result(None), _Result(existing)])

    result, claimed = await _manager(session).claim_task(TASK_NAME, TASK_ARGS)

    assert claimed is False
    assert result is existing
    assert result.result == {"inserted_chunks": 7}
    assert session.rollbacks == 0


@pytest.mark.asyncio
async def test_claim_skips_when_existing_task_is_recent():
    existing = _Record("STARTED", started_at=_now())
    session = _Session([_Result(None), _Result(existing)])

    result, claimed = await _manager(session).claim_task(TASK_NAME, TASK_ARGS)

    assert claimed is False
    assert result is existing
    assert session.rollbacks == 0


@pytest.mark.asyncio
async def test_claim_takes_over_failed_task():
    existing = _Record("FAILURE", started_at=_now() - timedelta(seconds=10))
    claimed_record = _Record("PENDING", execution_id=2)
    session = _Session([_Result(None), _Result(existing), _Result(claimed_record)])

    result, claimed = await _manager(session).claim_task(TASK_NAME, TASK_ARGS)

    assert claimed is True
    assert result is claimed_record
    assert session.commits == 1


@pytest.mark.asyncio
async def test_claim_takes_over_stale_task():
    stale = _now() - timedelta(seconds=700)
    existing = _Record("STARTED", started_at=stale)
    claimed_record = _Record("PENDING", execution_id=2)
    session = _Session([_Result(None), _Result(existing), _Result(claimed_record)])

    result, claimed = await _manager(session).claim_task(
        TASK_NAME, TASK_ARGS, task_time_limit=600
    )

    assert claimed is True
    assert result is claimed_record


@pytest.mark.asyncio
async def test_claim_loses_retry_race_to_another_worker():
    existing = _Record("FAILURE", started_at=_now() - timedelta(seconds=10))
    # The guarded UPDATE matched no row: another worker claimed it first.
    session = _Session([_Result(None), _Result(existing), _Result(None)])

    result, claimed = await _manager(session).claim_task(TASK_NAME, TASK_ARGS)

    assert claimed is False
    assert result is existing


def test_args_hash_is_stable_and_argument_sensitive():
    manager = _manager(_Session([]))

    first = manager.create_args_hash(TASK_NAME, TASK_ARGS)
    reordered = manager.create_args_hash(
        TASK_NAME, {"file_id": "policy.txt", "project_id": 1}
    )
    different = manager.create_args_hash(
        TASK_NAME, {**TASK_ARGS, "do_reset": 1}
    )

    assert first == reordered
    assert first != different
