from pathlib import Path

from fastapi.testclient import TestClient

from expenses.web import app as web

FIXTURES = Path(__file__).parent / "fixtures"


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setattr(web, "STATEMENTS_DIR", FIXTURES)
    monkeypatch.setattr(web, "HISTORY_DIR", tmp_path / "history")
    web._cache.clear()
    return TestClient(web.app)


def test_health(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    assert client.get("/api/health").json() == {"status": "ok"}


def test_month_list_and_detail(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)

    months = client.get("/api/months").json()["months"]
    assert any(m["month"] == "2024-01" for m in months)

    detail = client.get("/api/months/2024-01").json()
    assert detail["report"]["transaction_count"] == 18
    assert len(detail["transactions"]) == 18


def test_unknown_month_returns_404(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    assert client.get("/api/months/1999-01").status_code == 404


def test_dashboard_is_served(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    response = client.get("/")
    assert response.status_code == 200
    assert "Expenses" in response.text


def test_manifest_and_icons_served(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    assert client.get("/manifest.webmanifest").status_code == 200
    assert client.get("/icons/icon-192.png").status_code == 200
