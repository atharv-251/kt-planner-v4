from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_controlled_sql_select_allowed():
    resp = client.post(
        "/api/v1/database/query",
        json={"query": "SELECT count(*) as total FROM transitions"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "columns" in data
    assert "rows" in data
    assert data["row_count"] >= 0

def test_controlled_sql_mutations_blocked():
    forbidden_queries = [
        "DROP TABLE transitions",
        "DELETE FROM transitions",
        "INSERT INTO transitions (id, name) VALUES ('1', 'bad')",
        "UPDATE transitions SET name = 'hacked'",
        "ALTER TABLE transitions ADD COLUMN hacked text",
    ]
    for q in forbidden_queries:
        resp = client.post(
            "/api/v1/database/query",
            json={"query": q}
        )
        assert resp.status_code in (400, 403), f"Query '{q}' should have been blocked!"

