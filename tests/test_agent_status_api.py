from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base, get_db
from app.main import create_app
from app.models import agent, log, run  # noqa: F401
from app.models.agent import RunAgent
from app.models.log import RunAgentLog
from app.models.enums import LogEventType, ReportSource, RunStatus


@pytest.fixture
def db_session_factory(tmp_path: Path):
    database_path = tmp_path / "test_agent_status_api.db"
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)

    try:
        yield session_factory
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def client(db_session_factory) -> Iterator[TestClient]:
    app = create_app()

    def override_get_db() -> Iterator[Session]:
        session = db_session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


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
