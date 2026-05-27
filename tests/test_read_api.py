from datetime import datetime, timezone

from sqlalchemy import update

from app.models.agent import RunAgent
from app.models.enums import RiskLevel, RiskStatus, RiskType, RunStatus
from app.models.log import RunAgentLog
from app.models.risk import RunRisk


def _create_run(client, run_code: str = "run-read-001") -> dict:
    response = client.post(
        "/api/v1/runs",
        headers={"x-api-token": "dev-token", "x-request-id": f"req-{run_code}"},
        json={
            "run_code": run_code,
            "run_name": "Read API run",
            "source_type": "codex",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def _register_agent(client, run_id: int, agent_code: str, agent_name: str, owner_scope: str) -> dict:
    response = client.post(
        f"/api/v1/runs/{run_id}/agents/register",
        headers={"x-api-token": "dev-token", "x-request-id": f"req-register-{agent_code}"},
        json={
            "agent_code": agent_code,
            "agent_name": agent_name,
            "role": "worker",
            "owner_scope": owner_scope,
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def _update_agent_status(
    client,
    run_id: int,
    agent_id: int,
    *,
    agent_name: str,
    status: str,
    phase: str,
    progress_percent: int,
    current_task: str,
    blocking_reason: str | None,
    risk_level: str,
    request_id: str,
):
    response = client.post(
        f"/api/v1/runs/{run_id}/agents/{agent_id}/status",
        headers={"x-api-token": "dev-token", "x-request-id": request_id},
        json={
            "agent_name": agent_name,
            "status": status,
            "phase": phase,
            "progress_percent": progress_percent,
            "current_task": current_task,
            "blocking_reason": blocking_reason,
            "risk_level": risk_level,
            "reported_at": "2026-05-25T12:00:00Z",
            "last_update_at": "2026-05-25T12:00:00Z",
            "reported_by": "codex-orchestrator",
            "report_source": "codex-orchestrator",
            "idempotency_key": f"idem-{request_id}",
        },
    )
    assert response.status_code == 200


def test_get_run_overview_returns_aggregated_counts(client, db_session_factory):
    run = _create_run(client)
    agent_a = _register_agent(client, run["id"], "agent-a", "Agent A", "backend")
    agent_b = _register_agent(client, run["id"], "agent-b", "Agent B", "frontend")

    _update_agent_status(
        client,
        run["id"],
        agent_a["id"],
        agent_name="Agent A",
        status="running",
        phase="implementation",
        progress_percent=60,
        current_task="Implementing overview query",
        blocking_reason=None,
        risk_level="medium",
        request_id="req-overview-a",
    )
    _update_agent_status(
        client,
        run["id"],
        agent_b["id"],
        agent_name="Agent B",
        status="blocked",
        phase="design",
        progress_percent=20,
        current_task="Waiting for API shape",
        blocking_reason="Need backend contract",
        risk_level="high",
        request_id="req-overview-b",
    )

    response = client.get(
        f"/api/v1/runs/{run['id']}/overview",
        headers={"x-api-token": "dev-token", "x-request-id": "req-overview-get"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["run_id"] == run["id"]
    assert payload["data"]["total_agents"] == 2
    assert payload["data"]["running_count"] == 1
    assert payload["data"]["blocked_count"] == 1
    assert payload["data"]["completed_count"] == 0
    assert payload["data"]["failed_count"] == 0
    assert payload["data"]["overall_progress"] == 40
    assert payload["data"]["phase_distribution"]["implementation"] == 1
    assert payload["data"]["phase_distribution"]["design"] == 1
    assert response.headers["x-request-id"] == "req-overview-get"


def test_monitor_snapshot_includes_codex_inventory_counts(client):
    response = client.get(
        "/api/v1/monitor",
        headers={"x-api-token": "dev-token", "x-request-id": "req-monitor"},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert "codex_session_count" in payload
    assert "codex_workspace_count" in payload
    assert payload["total_runs"] >= 0


def test_get_agents_supports_blocked_filter_and_detail_lookup(client):
    run = _create_run(client, "run-read-002")
    blocked_agent = _register_agent(client, run["id"], "agent-blocked", "Blocked Agent", "audit")
    ready_agent = _register_agent(client, run["id"], "agent-ready", "Ready Agent", "ui")

    _update_agent_status(
        client,
        run["id"],
        blocked_agent["id"],
        agent_name="Blocked Agent",
        status="blocked",
        phase="implementation",
        progress_percent=45,
        current_task="Waiting for approval",
        blocking_reason="Approval pending",
        risk_level="high",
        request_id="req-blocked",
    )
    _update_agent_status(
        client,
        run["id"],
        ready_agent["id"],
        agent_name="Ready Agent",
        status="running",
        phase="test",
        progress_percent=80,
        current_task="Running regression tests",
        blocking_reason=None,
        risk_level="low",
        request_id="req-ready",
    )

    list_response = client.get(
        f"/api/v1/runs/{run['id']}/agents",
        headers={"x-api-token": "dev-token", "x-request-id": "req-agent-list"},
        params={"blocked_only": "true"},
    )
    detail_response = client.get(
        f"/api/v1/runs/{run['id']}/agents/{blocked_agent['id']}",
        headers={"x-api-token": "dev-token", "x-request-id": "req-agent-detail"},
    )

    assert list_response.status_code == 200
    list_payload = list_response.json()["data"]
    assert len(list_payload["items"]) == 1
    assert list_payload["items"][0]["agent_code"] == "agent-blocked"
    assert list_payload["items"][0]["status"] == "blocked"

    assert detail_response.status_code == 200
    detail_payload = detail_response.json()["data"]
    assert detail_payload["id"] == blocked_agent["id"]
    assert detail_payload["agent_code"] == "agent-blocked"
    assert detail_payload["blocking_reason"] == "Approval pending"
    assert detail_payload["current_task"] == "Waiting for approval"


def test_get_timeline_and_risks_return_latest_records(client, db_session_factory):
    run = _create_run(client, "run-read-003")
    agent = _register_agent(client, run["id"], "agent-risk", "Risk Agent", "security")

    _update_agent_status(
        client,
        run["id"],
        agent["id"],
        agent_name="Risk Agent",
        status="blocked",
        phase="implementation",
        progress_percent=30,
        current_task="Checking approval evidence",
        blocking_reason="Waiting for risk acceptance",
        risk_level="high",
        request_id="req-risk-status",
    )

    with db_session_factory() as session:
        session.execute(
            update(RunAgent)
            .where(RunAgent.id == agent["id"])
            .values(deliverable_summary="Audit summary pending", conversation_ref="thread-123")
        )
        session.add(
            RunRisk(
                run_id=run["id"],
                agent_id=agent["id"],
                risk_type=RiskType.BLOCKER,
                risk_level=RiskLevel.HIGH,
                title="Awaiting risk approval",
                reason="Security review not completed",
                suggested_action="Escalate to reviewer",
                status=RiskStatus.OPEN,
                opened_at=datetime(2026, 5, 25, 12, 5, tzinfo=timezone.utc),
                reported_by="codex-orchestrator",
            )
        )
        session.commit()

    timeline_response = client.get(
        f"/api/v1/runs/{run['id']}/timeline",
        headers={"x-api-token": "dev-token", "x-request-id": "req-timeline"},
    )
    risks_response = client.get(
        f"/api/v1/runs/{run['id']}/risks",
        headers={"x-api-token": "dev-token", "x-request-id": "req-risks"},
    )

    assert timeline_response.status_code == 200
    timeline_items = timeline_response.json()["data"]["items"]
    assert len(timeline_items) >= 1
    assert timeline_items[0]["agent_id"] == agent["id"]
    assert timeline_items[0]["event_type"] == "status_change"
    assert timeline_items[0]["summary"] == "agent status updated to blocked"

    assert risks_response.status_code == 200
    risk_items = risks_response.json()["data"]["items"]
    assert len(risk_items) == 1
    assert risk_items[0]["agent_id"] == agent["id"]
    assert risk_items[0]["title"] == "Awaiting risk approval"
    assert risk_items[0]["status"] == "open"
