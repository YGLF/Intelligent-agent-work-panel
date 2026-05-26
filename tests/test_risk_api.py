from datetime import datetime, timezone

from sqlalchemy import select

from app.models.agent import RunAgent
from app.models.enums import LogEventType, ReportSource, RiskLevel, RiskStatus, RiskType
from app.models.log import RunAgentLog
from app.models.risk import RunRisk


def _create_run(client, run_code: str = "run-risk-api-001") -> dict:
    response = client.post(
        "/api/v1/runs",
        headers={"x-api-token": "dev-token", "x-request-id": f"req-{run_code}"},
        json={
            "run_code": run_code,
            "run_name": "Risk API run",
            "source_type": "codex",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def _register_agent(client, run_id: int, agent_code: str = "agent-risk-api", agent_name: str = "Risk API Agent") -> dict:
    response = client.post(
        f"/api/v1/runs/{run_id}/agents/register",
        headers={"x-api-token": "dev-token", "x-request-id": f"req-register-{agent_code}"},
        json={
            "agent_code": agent_code,
            "agent_name": agent_name,
            "role": "worker",
            "owner_scope": "risk",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def test_open_risk_persists_lifecycle_record_and_audit_log(client, db_session_factory):
    run = _create_run(client)
    agent = _register_agent(client, run["id"])
    payload = {
        "risk_type": "blocker",
        "risk_level": "high",
        "title": "Pending production approval",
        "reason": "Change window approval is still outstanding",
        "suggested_action": "Escalate to release manager",
        "opened_at": "2026-05-26T09:00:00Z",
        "reported_by": "codex-orchestrator",
        "report_source": "reporter",
        "idempotency_key": "idem-risk-open-001",
    }

    response = client.post(
        f"/api/v1/runs/{run['id']}/agents/{agent['id']}/risk",
        headers={"x-api-token": "dev-token", "x-request-id": "req-risk-open-001"},
        json=payload,
    )
    duplicate = client.post(
        f"/api/v1/runs/{run['id']}/agents/{agent['id']}/risk",
        headers={"x-api-token": "dev-token", "x-request-id": "req-risk-open-002"},
        json=payload,
    )

    assert response.status_code == 201
    assert duplicate.status_code == 201
    payload = response.json()["data"]
    assert payload["risk_type"] == "blocker"
    assert payload["risk_level"] == "high"
    assert payload["status"] == "open"
    assert response.headers["x-request-id"] == "req-risk-open-001"

    with db_session_factory() as session:
        persisted_risk = session.scalar(
            select(RunRisk)
            .where(RunRisk.agent_id == agent["id"], RunRisk.title == "Pending production approval")
            .order_by(RunRisk.id.desc())
        )
        persisted_risks = session.scalars(
            select(RunRisk).where(RunRisk.agent_id == agent["id"], RunRisk.title == "Pending production approval")
        ).all()
        persisted_agent = session.scalar(select(RunAgent).where(RunAgent.id == agent["id"]))
        persisted_log = session.scalar(
            select(RunAgentLog)
            .where(RunAgentLog.agent_id == agent["id"], RunAgentLog.idempotency_key == "idem-risk-open-001")
            .order_by(RunAgentLog.id.desc())
        )

        assert persisted_risk is not None
        assert len(persisted_risks) == 1
        assert persisted_risk.risk_type == RiskType.BLOCKER
        assert persisted_risk.risk_level == RiskLevel.HIGH
        assert persisted_risk.status == RiskStatus.OPEN
        assert persisted_risk.reported_by == "codex-orchestrator"
        assert persisted_risk.opened_at == datetime(2026, 5, 26, 9, 0, tzinfo=timezone.utc).replace(tzinfo=None)

        assert persisted_agent is not None
        assert persisted_agent.risk_level == RiskLevel.HIGH
        assert persisted_agent.version_no == 2

        assert persisted_log is not None
        assert persisted_log.event_type == LogEventType.COMMENT
        assert persisted_log.report_source == ReportSource.REPORTER
        assert persisted_log.request_id == "req-risk-open-001"
        assert persisted_log.summary == "risk opened: Pending production approval"


def test_resolve_risk_is_idempotent_and_updates_lifecycle_fields(client, db_session_factory):
    run = _create_run(client, "run-risk-api-002")
    agent = _register_agent(client, run["id"], "agent-risk-resolve", "Risk Resolve Agent")

    open_response = client.post(
        f"/api/v1/runs/{run['id']}/agents/{agent['id']}/risk",
        headers={"x-api-token": "dev-token", "x-request-id": "req-risk-open-002"},
        json={
            "risk_type": "dependency",
            "risk_level": "medium",
            "title": "Awaiting dependency signoff",
            "reason": "Upstream package owner has not approved rollout",
            "suggested_action": "Follow up with upstream owner",
            "opened_at": "2026-05-26T10:00:00Z",
            "reported_by": "codex-orchestrator",
            "report_source": "reporter",
            "idempotency_key": "idem-risk-open-002",
        },
    )
    risk_id = open_response.json()["data"]["id"]

    payload = {
        "status": "resolved",
        "resolved_at": "2026-05-26T11:30:00Z",
        "resolved_by": "release-manager",
        "resolution_note": "Dependency signoff completed",
        "report_source": "api",
        "idempotency_key": "idem-risk-resolve-001",
    }
    first = client.post(
        f"/api/v1/runs/{run['id']}/agents/{agent['id']}/risks/{risk_id}/resolve",
        headers={"x-api-token": "dev-token", "x-request-id": "req-risk-resolve-1"},
        json=payload,
    )
    second = client.post(
        f"/api/v1/runs/{run['id']}/agents/{agent['id']}/risks/{risk_id}/resolve",
        headers={"x-api-token": "dev-token", "x-request-id": "req-risk-resolve-2"},
        json=payload,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["data"]["status"] == "resolved"

    with db_session_factory() as session:
        persisted_risk = session.scalar(select(RunRisk).where(RunRisk.id == risk_id))
        persisted_agent = session.scalar(select(RunAgent).where(RunAgent.id == agent["id"]))
        persisted_logs = session.scalars(
            select(RunAgentLog)
            .where(RunAgentLog.agent_id == agent["id"], RunAgentLog.idempotency_key == "idem-risk-resolve-001")
            .order_by(RunAgentLog.id.asc())
        ).all()

        assert persisted_risk is not None
        assert persisted_risk.status == RiskStatus.RESOLVED
        assert persisted_risk.resolved_by == "release-manager"
        assert persisted_risk.duration_seconds_snapshot == 5400
        assert persisted_risk.resolved_at == datetime(2026, 5, 26, 11, 30, tzinfo=timezone.utc).replace(tzinfo=None)

        assert persisted_agent is not None
        assert persisted_agent.risk_level == RiskLevel.LOW
        assert len(persisted_logs) == 1
        assert persisted_logs[0].summary == "risk resolved: Awaiting dependency signoff"
