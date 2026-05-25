from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.agent import RunAgent
from app.models.enums import LogEventType, RunStatus
from app.models.run import Run
from app.schemas.agent import AgentRegister, AgentStatusUpdate
from app.services.audit import append_agent_audit_log


def register_agent(db: Session, run: Run, payload: AgentRegister) -> RunAgent:
    agent = RunAgent(
        run_id=run.id,
        agent_code=payload.agent_code,
        agent_name=payload.agent_name,
        role=payload.role,
        owner_scope=payload.owner_scope,
    )
    db.add(agent)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise

    db.refresh(agent)
    return agent


def update_agent_status(
    db: Session,
    *,
    agent: RunAgent,
    payload: AgentStatusUpdate,
) -> RunAgent:
    old_status = agent.status
    old_phase = agent.phase
    before_progress = agent.progress_percent

    agent.agent_name = payload.agent_name
    agent.status = payload.status
    agent.phase = payload.phase
    agent.progress_percent = payload.progress_percent
    agent.current_task = payload.current_task
    agent.blocking_reason = payload.blocking_reason
    agent.risk_level = payload.risk_level
    agent.last_update_at = payload.last_update_at
    agent.version_no = (agent.version_no or 1) + 1

    if payload.status == RunStatus.RUNNING and agent.started_at is None:
        agent.started_at = payload.reported_at
    if payload.status in {RunStatus.COMPLETED, RunStatus.FAILED}:
        agent.finished_at = payload.last_update_at
    if payload.status == RunStatus.BLOCKED:
        agent.needs_input = True

    append_agent_audit_log(
        db,
        agent=agent,
        event_type=LogEventType.STATUS_CHANGE,
        summary=f"agent status updated to {payload.status}",
        reported_by=payload.reported_by,
        report_source=payload.report_source,
        request_id=payload.request_id,
        idempotency_key=payload.idempotency_key,
        occurred_at=payload.reported_at,
        old_status=old_status,
        new_status=payload.status,
        old_phase=old_phase,
        new_phase=payload.phase,
        before_progress=before_progress,
        after_progress=payload.progress_percent,
        detail_json={
            "agent_name": payload.agent_name,
            "current_task": payload.current_task,
            "blocking_reason": payload.blocking_reason,
            "risk_level": payload.risk_level,
        },
    )

    db.commit()
    db.refresh(agent)
    return agent
