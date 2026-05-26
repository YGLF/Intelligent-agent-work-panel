import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import agent, log, run  # noqa: F401
from app.models.agent import RunAgent
from app.models.log import RunAgentLog
from app.models.enums import LogEventType, ReportSource, RunStatus


@pytest.fixture
def seeded_run(client: TestClient):
    response = client.post(
        "/api/v1/runs",
        headers={"x-api-token": "dev-token", "x-request-id": "req-seed-run"},
        json={
            "run_code": "run-seeded",
            "run_name": "Seeded run",
            "source_type": "codex",
        },
    )

    assert response.status_code == 201
    return response.json()["data"]


def test_status_update_writes_snapshot_and_audit_log(client, seeded_run, db_session_factory):
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
            "request_id": "req-body-ignored",
            "idempotency_key": "idem-status-001",
        },
    )

    assert register_response.status_code == 201
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["status"] == "blocked"
    assert payload["risk_level"] == "high"

    with db_session_factory() as session:
        persisted_agent = session.scalar(select(RunAgent).where(RunAgent.id == agent_id))
        persisted_log = session.scalar(
            select(RunAgentLog)
            .where(RunAgentLog.agent_id == agent_id)
            .order_by(RunAgentLog.id.desc())
        )

        assert persisted_agent is not None
        assert persisted_agent.status == RunStatus.BLOCKED
        assert persisted_agent.phase.value == "implementation"
        assert persisted_agent.progress_percent == 45
        assert persisted_agent.current_task == "Reviewing audit hooks"
        assert persisted_agent.blocking_reason == "Need schema approval"
        assert persisted_agent.risk_level.value == "high"
        assert persisted_agent.last_update_at.isoformat() == "2026-05-25T12:00:00"

        assert persisted_log is not None
        assert persisted_log.event_type == LogEventType.STATUS_CHANGE
        assert persisted_log.old_status == RunStatus.PENDING
        assert persisted_log.new_status == RunStatus.BLOCKED
        assert persisted_log.after_progress == 45
        assert persisted_log.request_id == "req-status"
        assert persisted_log.idempotency_key == "idem-status-001"
        assert persisted_log.reported_by == "codex-orchestrator"
        assert persisted_log.report_source == ReportSource.SYSTEM
        assert persisted_log.summary == "agent status updated to blocked"


def test_status_update_is_idempotent_for_same_agent_and_key(client, seeded_run, db_session_factory):
    register_response = client.post(
        f"/api/v1/runs/{seeded_run['id']}/agents/register",
        headers={"x-api-token": "dev-token", "x-request-id": "req-register-idem"},
        json={
            "agent_code": "agent-idempotent",
            "agent_name": "Idempotent Agent",
            "role": "backend",
            "owner_scope": "api",
        },
    )
    agent_id = register_response.json()["data"]["id"]
    payload = {
        "agent_name": "Idempotent Agent",
        "status": "running",
        "phase": "implementation",
        "progress_percent": 55,
        "current_task": "Applying idempotent update",
        "blocking_reason": None,
        "risk_level": "medium",
        "reported_at": "2026-05-25T14:00:00Z",
        "last_update_at": "2026-05-25T14:00:00Z",
        "reported_by": "codex-orchestrator",
        "report_source": "reporter",
        "idempotency_key": "idem-status-repeat-001",
    }

    first = client.post(
        f"/api/v1/runs/{seeded_run['id']}/agents/{agent_id}/status",
        headers={"x-api-token": "dev-token", "x-request-id": "req-status-repeat-1"},
        json=payload,
    )
    second = client.post(
        f"/api/v1/runs/{seeded_run['id']}/agents/{agent_id}/status",
        headers={"x-api-token": "dev-token", "x-request-id": "req-status-repeat-2"},
        json=payload,
    )

    assert first.status_code == 200
    assert second.status_code == 200

    with db_session_factory() as session:
        persisted_agent = session.scalar(select(RunAgent).where(RunAgent.id == agent_id))
        persisted_logs = session.scalars(
            select(RunAgentLog)
            .where(RunAgentLog.agent_id == agent_id, RunAgentLog.idempotency_key == "idem-status-repeat-001")
            .order_by(RunAgentLog.id.asc())
        ).all()

        assert persisted_agent is not None
        assert persisted_agent.version_no == 2
        assert len(persisted_logs) == 1


def test_status_update_persists_codex_extension_fields(client, seeded_run, db_session_factory):
    register_response = client.post(
        f"/api/v1/runs/{seeded_run['id']}/agents/register",
        headers={"x-api-token": "dev-token", "x-request-id": "req-register-codex"},
        json={
            "agent_code": "agent-codex",
            "agent_name": "Codex Agent",
            "role": "worker",
            "owner_scope": "codex",
        },
    )
    agent_id = register_response.json()["data"]["id"]

    response = client.post(
        f"/api/v1/runs/{seeded_run['id']}/agents/{agent_id}/status",
        headers={"x-api-token": "dev-token", "x-request-id": "req-status-codex"},
        json={
            "agent_name": "Codex Agent",
            "status": "running",
            "phase": "implementation",
            "progress_percent": 20,
            "current_task": "Working on bridge integration",
            "blocking_reason": None,
            "depends_on": ["agent-a", "agent-b"],
            "handoff_to": "agent-b",
            "needs_input": False,
            "deliverable_summary": "Bridge skeleton is ready",
            "codex_agent_type": "planner",
            "conversation_ref": "conv-123",
            "started_at": "2026-05-25T15:00:00Z",
            "finished_at": None,
            "last_heartbeat_at": "2026-05-25T15:05:00Z",
            "ready_for_integration": True,
            "risk_level": "low",
            "reported_at": "2026-05-25T15:05:00Z",
            "last_update_at": "2026-05-25T15:05:00Z",
            "reported_by": "codex-orchestrator",
            "report_source": "reporter",
            "idempotency_key": "idem-status-codex-001",
        },
    )

    assert response.status_code == 200

    with db_session_factory() as session:
        persisted_agent = session.scalar(select(RunAgent).where(RunAgent.id == agent_id))
        assert persisted_agent is not None
        assert persisted_agent.depends_on_json == ["agent-a", "agent-b"]
        assert persisted_agent.handoff_to == "agent-b"
        assert persisted_agent.needs_input is False
        assert persisted_agent.deliverable_summary == "Bridge skeleton is ready"
        assert persisted_agent.codex_agent_type == "planner"
        assert persisted_agent.conversation_ref == "conv-123"
        assert persisted_agent.last_heartbeat_at.isoformat() == "2026-05-25T15:05:00"


def test_register_agent_not_found_emits_rejection_audit_log(client, caplog):
    with caplog.at_level("WARNING", logger="app.audit"):
        response = client.post(
            "/api/v1/runs/999/agents/register",
            headers={"x-api-token": "dev-token", "x-request-id": "req-register-missing-run"},
            json={
                "agent_code": "agent-missing-run",
                "agent_name": "Missing Run Agent",
                "role": "ops",
                "owner_scope": "audit",
            },
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "run not found"}
    assert '"action": "register_run_agent"' in caplog.text
    assert '"request_id": "req-register-missing-run"' in caplog.text
    assert '"reason": "run not found"' in caplog.text
    assert '"run_id": 999' in caplog.text
    assert '"actor": "token-authenticated-caller"' in caplog.text
