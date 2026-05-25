from conftest import make_client


def test_health_endpoint_returns_service_metadata():
    with make_client() as client:
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
