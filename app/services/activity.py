from datetime import datetime, timezone

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.agent import RunAgent
from app.models.artifact import RunAgentArtifact
from app.models.enums import LogEventType
from app.models.log import RunAgentLog
from app.schemas.artifact import AgentArtifactCreate
from app.schemas.log import AgentLogCreate
from app.services.audit import build_agent_log, find_existing_agent_log


def _find_existing_agent_artifact(
    db: Session,
    *,
    agent_id: int,
    payload: AgentArtifactCreate,
    created_by: str,
) -> RunAgentArtifact | None:
    if not payload.idempotency_key:
        return None

    stmt: Select[tuple[RunAgentArtifact]] = (
        select(RunAgentArtifact)
        .where(
            RunAgentArtifact.agent_id == agent_id,
            RunAgentArtifact.artifact_type == payload.artifact_type,
            RunAgentArtifact.artifact_name == payload.artifact_name,
            RunAgentArtifact.artifact_uri == payload.artifact_uri,
            RunAgentArtifact.created_by == created_by,
        )
        .order_by(RunAgentArtifact.id.asc())
    )

    if payload.artifact_version is None:
        stmt = stmt.where(RunAgentArtifact.artifact_version.is_(None))
    else:
        stmt = stmt.where(RunAgentArtifact.artifact_version == payload.artifact_version)

    if payload.summary is None:
        stmt = stmt.where(RunAgentArtifact.summary.is_(None))
    else:
        stmt = stmt.where(RunAgentArtifact.summary == payload.summary)

    return db.scalar(stmt)


def _find_existing_artifact_from_idempotency(
    db: Session,
    *,
    agent_id: int,
    idempotency_key: str | None,
) -> RunAgentArtifact | None:
    if not idempotency_key:
        return None

    existing_artifact = db.scalar(
        select(RunAgentArtifact).where(
            RunAgentArtifact.agent_id == agent_id,
            RunAgentArtifact.idempotency_key == idempotency_key,
        )
    )
    if existing_artifact is not None:
        return existing_artifact

    existing_log = find_existing_agent_log(
        db,
        agent_id=agent_id,
        idempotency_key=idempotency_key,
    )
    if existing_log is None or not isinstance(existing_log.detail_json, dict):
        return None

    artifact_id = existing_log.detail_json.get("artifact_id")
    if not isinstance(artifact_id, int):
        return None

    artifact = db.get(RunAgentArtifact, artifact_id)
    if artifact is None or artifact.agent_id != agent_id:
        return None
    return artifact


def append_agent_log(
    db: Session,
    *,
    agent: RunAgent,
    payload: AgentLogCreate,
    request_id: str,
) -> RunAgentLog:
    existing_log = find_existing_agent_log(
        db,
        agent_id=agent.id,
        idempotency_key=payload.idempotency_key,
    )
    if existing_log is not None:
        return existing_log

    log = build_agent_log(
        agent=agent,
        event_type=payload.event_type,
        summary=payload.summary,
        reported_by=payload.reported_by,
        report_source=payload.report_source,
        request_id=request_id,
        idempotency_key=payload.idempotency_key,
        occurred_at=payload.occurred_at,
        detail_json=payload.detail_json,
    )
    db.add(log)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing_log = find_existing_agent_log(
            db,
            agent_id=agent.id,
            idempotency_key=payload.idempotency_key,
        )
        if existing_log is not None:
            return existing_log
        raise
    db.refresh(log)
    return log


def register_agent_artifact(
    db: Session,
    *,
    agent: RunAgent,
    payload: AgentArtifactCreate,
    created_by: str,
    request_id: str,
) -> RunAgentArtifact:
    existing_artifact = _find_existing_artifact_from_idempotency(
        db,
        agent_id=agent.id,
        idempotency_key=payload.idempotency_key,
    )
    if existing_artifact is not None:
        return existing_artifact

    existing_artifact = _find_existing_agent_artifact(
        db,
        agent_id=agent.id,
        payload=payload,
        created_by=created_by,
    )
    if existing_artifact is not None:
        return existing_artifact

    artifact = RunAgentArtifact(
        run_id=agent.run_id,
        agent_id=agent.id,
        artifact_type=payload.artifact_type,
        artifact_name=payload.artifact_name,
        artifact_uri=payload.artifact_uri,
        artifact_version=payload.artifact_version,
        summary=payload.summary,
        idempotency_key=payload.idempotency_key,
        created_by=created_by,
    )
    db.add(artifact)
    db.flush()
    occurred_at = artifact.created_at or datetime.now(timezone.utc)

    audit_log = build_agent_log(
        agent=agent,
        event_type=LogEventType.COMMENT,
        summary=f"artifact registered: {payload.artifact_name}",
        reported_by=created_by,
        report_source="api",
        request_id=request_id,
        idempotency_key=payload.idempotency_key,
        occurred_at=occurred_at,
        detail_json={
            "artifact_id": artifact.id,
            "artifact_type": payload.artifact_type.value,
            "artifact_name": payload.artifact_name,
            "artifact_uri": payload.artifact_uri,
            "artifact_version": payload.artifact_version,
        },
    )
    db.add(audit_log)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        replayed_artifact = _find_existing_artifact_from_idempotency(
            db,
            agent_id=agent.id,
            idempotency_key=payload.idempotency_key,
        )
        if replayed_artifact is not None:
            return replayed_artifact
        raise
    db.refresh(artifact)
    return artifact
