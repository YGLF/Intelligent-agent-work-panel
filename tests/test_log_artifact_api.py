from sqlalchemy import select

from app.models.artifact import RunAgentArtifact
from app.models.log import RunAgentLog
from app.models.enums import ArtifactType, LogEventType, ReportSource


def _create_run(client, run_code: str = "run-log-001") -> dict:
    response = client.post(
        "/api/v1/runs",
        headers={"x-api-token": "dev-token", "x-request-id": f"req-{run_code}"},
        json={
            "run_code": run_code,
            "run_name": "Log Artifact Run",
            "source_type": "codex",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def _register_agent(client, run_id: int, agent_code: str = "agent-log", agent_name: str = "Log Agent") -> dict:
    response = client.post(
        f"/api/v1/runs/{run_id}/agents/register",
        headers={"x-api-token": "dev-token", "x-request-id": f"req-register-{agent_code}"},
        json={
            "agent_code": agent_code,
            "agent_name": agent_name,
            "role": "worker",
            "owner_scope": "audit",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def test_append_log_persists_timeline_entry(client, db_session_factory):
    run = _create_run(client)
    agent = _register_agent(client, run["id"])

    response = client.post(
        f"/api/v1/runs/{run['id']}/agents/{agent['id']}/log",
        headers={"x-api-token": "dev-token", "x-request-id": "req-log-001"},
        json={
            "event_type": "comment",
            "summary": "Manual checkpoint note",
            "detail_json": {"remark": "Waiting for integration"},
            "reported_by": "codex-orchestrator",
            "report_source": "reporter",
            "occurred_at": "2026-05-26T10:00:00Z",
            "idempotency_key": "idem-log-001",
        },
    )

    assert response.status_code == 201
    payload = response.json()["data"]
    assert payload["event_type"] == "comment"
    assert payload["summary"] == "Manual checkpoint note"

    with db_session_factory() as session:
        persisted = session.scalar(
            select(RunAgentLog)
            .where(RunAgentLog.agent_id == agent["id"], RunAgentLog.summary == "Manual checkpoint note")
        )
        assert persisted is not None
        assert persisted.event_type == LogEventType.COMMENT
        assert persisted.report_source == ReportSource.REPORTER
        assert persisted.request_id == "req-log-001"


def test_register_artifact_persists_agent_deliverable(client, db_session_factory):
    run = _create_run(client, "run-artifact-001")
    agent = _register_agent(client, run["id"], "agent-artifact", "Artifact Agent")

    response = client.post(
        f"/api/v1/runs/{run['id']}/agents/{agent['id']}/artifact",
        headers={"x-api-token": "dev-token", "x-request-id": "req-artifact-001"},
        json={
            "artifact_type": "summary",
            "artifact_name": "Integration summary",
            "artifact_uri": "https://example.invalid/artifacts/summary-001",
            "artifact_version": "v1",
            "summary": "Collected validation notes",
        },
    )

    assert response.status_code == 201
    payload = response.json()["data"]
    assert payload["artifact_type"] == "summary"
    assert payload["artifact_name"] == "Integration summary"

    with db_session_factory() as session:
        persisted = session.scalar(
            select(RunAgentArtifact)
            .where(RunAgentArtifact.agent_id == agent["id"], RunAgentArtifact.artifact_name == "Integration summary")
        )
        assert persisted is not None
        assert persisted.artifact_type == ArtifactType.SUMMARY
        assert persisted.created_by == "token:dev-token"
        assert persisted.idempotency_key is None
        audit_log = session.scalar(
            select(RunAgentLog)
            .where(RunAgentLog.agent_id == agent["id"], RunAgentLog.request_id == "req-artifact-001")
        )
        assert audit_log is not None
        assert audit_log.event_type == LogEventType.COMMENT
        assert audit_log.detail_json["artifact_id"] == persisted.id
        assert audit_log.detail_json["artifact_type"] == "summary"


def test_register_artifact_is_idempotent_for_same_agent_and_key(client, db_session_factory):
    run = _create_run(client, "run-artifact-idem-001")
    agent = _register_agent(client, run["id"], "agent-artifact-idem", "Artifact Idem Agent")
    first_payload = {
        "artifact_type": "summary",
        "artifact_name": "Repeat-safe summary",
        "artifact_uri": "https://example.invalid/artifacts/repeat-safe-summary",
        "artifact_version": "v2",
        "summary": "Stable artifact payload",
        "idempotency_key": "idem-artifact-repeat-001",
    }
    second_payload = {
        **first_payload,
        "artifact_uri": "https://example.invalid/artifacts/repeat-safe-summary-v2",
        "summary": "Mutated duplicate payload",
    }

    first = client.post(
        f"/api/v1/runs/{run['id']}/agents/{agent['id']}/artifact",
        headers={"x-api-token": "dev-token", "x-request-id": "req-artifact-repeat-1"},
        json=first_payload,
    )
    second = client.post(
        f"/api/v1/runs/{run['id']}/agents/{agent['id']}/artifact",
        headers={"x-api-token": "dev-token", "x-request-id": "req-artifact-repeat-2"},
        json=second_payload,
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["data"]["id"] == second.json()["data"]["id"]
    assert second.json()["data"]["artifact_uri"] == first_payload["artifact_uri"]

    with db_session_factory() as session:
        persisted = session.scalars(
            select(RunAgentArtifact).where(
                RunAgentArtifact.agent_id == agent["id"],
                RunAgentArtifact.artifact_name == "Repeat-safe summary",
            )
        ).all()
        assert len(persisted) == 1
        assert persisted[0].idempotency_key == "idem-artifact-repeat-001"
        audit_logs = session.scalars(
            select(RunAgentLog)
            .where(RunAgentLog.agent_id == agent["id"], RunAgentLog.idempotency_key == "idem-artifact-repeat-001")
            .order_by(RunAgentLog.id.asc())
        ).all()
        assert len(audit_logs) == 1


def test_append_log_is_idempotent_for_same_agent_and_key(client, db_session_factory):
    run = _create_run(client, "run-log-idem-001")
    agent = _register_agent(client, run["id"], "agent-log-idem", "Log Idem Agent")
    payload = {
        "event_type": "comment",
        "summary": "Stable duplicate note",
        "detail_json": {"remark": "Repeat-safe"},
        "reported_by": "codex-orchestrator",
        "report_source": "reporter",
        "occurred_at": "2026-05-26T10:10:00Z",
        "idempotency_key": "idem-log-repeat-001",
    }

    first = client.post(
        f"/api/v1/runs/{run['id']}/agents/{agent['id']}/log",
        headers={"x-api-token": "dev-token", "x-request-id": "req-log-repeat-1"},
        json=payload,
    )
    second = client.post(
        f"/api/v1/runs/{run['id']}/agents/{agent['id']}/log",
        headers={"x-api-token": "dev-token", "x-request-id": "req-log-repeat-2"},
        json=payload,
    )

    assert first.status_code == 201
    assert second.status_code == 201

    with db_session_factory() as session:
        persisted = session.scalars(
            select(RunAgentLog)
            .where(RunAgentLog.agent_id == agent["id"], RunAgentLog.idempotency_key == "idem-log-repeat-001")
            .order_by(RunAgentLog.id.asc())
        ).all()
        assert len(persisted) == 1
