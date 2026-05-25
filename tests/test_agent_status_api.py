from app.models import agent, log, run  # noqa: F401


def test_status_update_writes_snapshot_and_audit_log(client, seeded_run):
    register_response = client.post(
        f"/api/v1/runs/{seeded_run['id']}/agents/register",
        headers={"x-api-token": "dev-token", "x-request-id": "req-register"},
        json={
            "agent_code": "agent-security",
            "agent_name": "Security Agent",
            "role": "security",
            "owner_scope": "audit",
        },
    )
    agent_id = register_response.json()["data"]["id"]

    response = client.post(
        f"/api/v1/runs/{seeded_run['id']}/agents/{agent_id}/status",
        headers={"x-api-token": "dev-token", "x-request-id": "req-status"},
        json={
            "agent_name": "Security Agent",
            "status": "blocked",
            "phase": "implementation",
            "progress_percent": 45,
            "current_task": "Reviewing audit hooks",
            "blocking_reason": "Need schema approval",
            "risk_level": "high",
            "reported_at": "2026-05-25T12:00:00Z",
            "last_update_at": "2026-05-25T12:00:00Z",
            "reported_by": "codex-orchestrator",
            "report_source": "codex-orchestrator",
            "request_id": "req-status",
            "idempotency_key": "idem-status-001",
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["status"] == "blocked"
    assert payload["risk_level"] == "high"
