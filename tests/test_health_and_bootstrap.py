from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint_returns_service_metadata():
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "code": "OK",
        "message": "service healthy",
        "data": {
            "service": "codex-agent-status-panel",
            "version": "0.1.0",
        },
    }
