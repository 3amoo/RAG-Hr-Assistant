from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from helpers.auth import verify_api_key
from helpers.config import get_settings


app = FastAPI()


@app.get("/protected", dependencies=[Depends(verify_api_key)])
def protected():
    return {"ok": True}


client = TestClient(app)


def test_open_local_access_when_no_api_key_configured():
    assert client.get("/protected").status_code == 200


def test_wrong_or_missing_key_is_rejected(monkeypatch):
    monkeypatch.setattr(get_settings(), "API_KEY", "secret")

    assert client.get("/protected").status_code == 401
    assert client.get(
        "/protected", headers={"X-API-Key": "wrong"}
    ).status_code == 401


def test_correct_key_is_accepted(monkeypatch):
    monkeypatch.setattr(get_settings(), "API_KEY", "secret")

    response = client.get("/protected", headers={"X-API-Key": "secret"})
    assert response.status_code == 200
    assert response.json() == {"ok": True}
