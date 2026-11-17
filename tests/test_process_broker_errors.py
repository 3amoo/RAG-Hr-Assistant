import asyncio
import json
from types import SimpleNamespace

from kombu.exceptions import OperationalError

from routes import data as data_routes
from routes.schemes.data import ProcessRequest


request_obj = SimpleNamespace()
process_request = ProcessRequest(file_id="file.txt")


def _raise_broker_error(*args, **kwargs):
    raise OperationalError("[Errno 111] Connection refused")


def test_process_returns_503_when_broker_is_down(monkeypatch):
    monkeypatch.setattr(data_routes.process_project_files, "delay", _raise_broker_error)

    response = asyncio.run(
        data_routes.process_endpoint(request_obj, 1, process_request)
    )

    assert response.status_code == 503
    assert "Task queue unavailable" in json.loads(response.body)["detail"]


def test_process_and_push_returns_503_when_broker_is_down(monkeypatch):
    monkeypatch.setattr(
        data_routes.process_and_push_workflow, "delay", _raise_broker_error
    )

    response = asyncio.run(
        data_routes.process_and_push_endpoint(request_obj, 1, process_request)
    )

    assert response.status_code == 503
    assert "Task queue unavailable" in json.loads(response.body)["detail"]
