from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.agent import RunAgent
from app.models.enums import LogEventType, RunStatus
from app.models.run import Run
from app.schemas.agent import AgentRegister, AgentStatusUpdate
from app.services.audit import append_agent_audit_log, find_existing_agent_log


def register_agent(db: Session, run: Run, payload: AgentRegister) -> RunAgent:
    agent = RunAgent(
        run_id=run.id,
        agent_code=payload.agent_code,
        agent_name=payload.agent_name,
        role=payload.role,
        owner_scope=payload.owner_scope,
        codex_agent_type=payload.codex_agent_type,
        model_name=payload.model_name,
        model_tier=payload.model_tier,
        is_main_agent=payload.is_main_agent,
        parent_agent_id=payload.parent_agent_id,
        conversation_ref=payload.conversation_ref,
    )
    db.add(agent)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(agent)
    return agent


def update_agent_status(
    db: Session,
    *,
    agent: RunAgent,
    payload: AgentStatusUpdate,
    audit_request_id: str,
) -> RunAgent:
    existing_log = find_existing_agent_log(
        db,
        agent_id=agent.id,
        idempotency_key=payload.idempotency_key,
    )
    if existing_log is not None:
        db.refresh(agent)
        return agent

    old_status = agent.status
    old_phase = agent.phase
    before_progress = agent.progress_percent

    agent.agent_name = payload.agent_name
    agent.status = payload.status
    agent.phase = payload.phase
    agent.progress_percent = payload.progress_percent
    agent.current_task = payload.current_task
    agent.blocking_reason = payload.blocking_reason
    agent.depends_on_json = payload.depends_on
    agent.handoff_to = payload.handoff_to
    if payload.needs_input is not None:
        agent.needs_input = payload.needs_input
    agent.deliverable_summary = payload.deliverable_summary
    agent.codex_agent_type = payload.codex_agent_type
    if payload.model_name is not None:
        agent.model_name = payload.model_name
    if payload.model_tier is not None:
        agent.model_tier = payload.model_tier
    if payload.is_main_agent is not None:
        agent.is_main_agent = payload.is_main_agent
    if payload.parent_agent_id is not None:
        agent.parent_agent_id = payload.parent_agent_id
    agent.conversation_ref = payload.conversation_ref
    agent.risk_level = payload.risk_level
    agent.last_update_at = payload.last_update_at
    if payload.last_heartbeat_at is not None:
        agent.last_heartbeat_at = payload.last_heartbeat_at
    if payload.started_at is not None:
        agent.started_at = payload.started_at
    if payload.finished_at is not None:
        agent.finished_at = payload.finished_at
    if payload.ready_for_integration is not None:
        agent.needs_input = not payload.ready_for_integration
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
        request_id=audit_request_id,
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
            db.refresh(agent)
            return agent
        raise
    db.refresh(agent)
    return agent
