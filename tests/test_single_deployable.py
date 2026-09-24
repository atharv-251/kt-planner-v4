from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_single_deployable_serves_frontend():
    # Test root endpoint returns HTML of React SPA
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "<!doctype html>" in resp.text.lower()
    assert "KT Planner" in resp.text

def test_single_deployable_serves_health_and_apis():
    # Test API endpoint
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["authoritative_db"] == "SQLite kt_planner.db"

