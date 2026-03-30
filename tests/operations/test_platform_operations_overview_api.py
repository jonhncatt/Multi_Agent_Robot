from fastapi.testclient import TestClient

from app.main import app


def test_platform_operations_overview_api_shape() -> None:
    client = TestClient(app)
    response = client.get("/api/operations/overview")
    assert response.status_code == 200
    payload = response.json()

    assert isinstance(payload.get("gates"), list)
    assert isinstance(payload.get("docs_index"), list)
    assert isinstance(payload.get("smoke_layers"), list)
    assert isinstance(payload.get("replay"), dict)

    gate_ids = {item.get("id") for item in payload.get("gates", [])}
    assert {"office", "research", "swarm"} <= gate_ids

    replay = payload.get("replay") or {}
    assert "root" in replay
    assert "families" in replay
