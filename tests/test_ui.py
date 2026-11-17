from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_root_redirects_to_ui():
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/ui/"


def test_ui_page_is_self_contained():
    response = client.get("/ui/")
    assert response.status_code == 200

    html = response.text
    assert "RAG-Hr-Assistant" in html
    assert 'id="ask"' in html
    assert 'id="api-base"' in html
    assert 'id="notice"' in html

    # Everything needed to render and call the API lives in this one file, so
    # opening it from disk still shows the form and an actionable notice.
    assert "<style>" in html
    assert "<script>" in html
    assert 'window.location.protocol === "file:"' in html
    assert 'src="app.js"' not in html
    assert 'href="style.css"' not in html
