from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.agent import RunAgent
from app.models.enums import LogEventType, RiskLevel, RiskStatus
from app.models.risk import RunRisk
from app.schemas.risk import AgentRiskCreate, AgentRiskResolve
from app.services.audit import build_agent_log, find_existing_agent_log


_RISK_PRIORITY = {
    RiskLevel.LOW: 0,
    RiskLevel.MEDIUM: 1,
    RiskLevel.HIGH: 2,
}


def _normalize_dt(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _recalculate_agent_risk_level(db: Session, agent_id: int) -> RiskLevel:
    active_risks = db.scalars(
        select(RunRisk).where(
            RunRisk.agent_id == agent_id,
            RunRisk.status.in_((RiskStatus.OPEN, RiskStatus.MITIGATED)),
        )
    ).all()
    if not active_risks:
        return RiskLevel.LOW
    return max((risk.risk_level for risk in active_risks), key=lambda level: _RISK_PRIORITY[level])


def open_agent_risk(
    db: Session,
    *,
    agent: RunAgent,
    payload: AgentRiskCreate,
    request_id: str,
) -> RunRisk:
    existing_log = find_existing_agent_log(db, agent_id=agent.id, idempotency_key=payload.idempotency_key)
    if existing_log is not None and isinstance(existing_log.detail_json, dict) and existing_log.detail_json.get("risk_id"):
        existing_risk = db.get(RunRisk, existing_log.detail_json["risk_id"])
        if existing_risk is not None:
            return existing_risk

    risk = RunRisk(
        run_id=agent.run_id,
        agent_id=agent.id,
        risk_type=payload.risk_type,
        risk_level=payload.risk_level,
        title=payload.title,
        reason=payload.reason,
        suggested_action=payload.suggested_action,
        status=RiskStatus.OPEN,
        opened_at=payload.opened_at,
        reported_by=payload.reported_by,
    )
    db.add(risk)
    db.flush()

    agent.risk_level = max(agent.risk_level, payload.risk_level, key=lambda level: _RISK_PRIORITY[level])
    agent.version_no = (agent.version_no or 1) + 1
    agent.last_update_at = payload.opened_at
    if agent.run is not None:
        agent.run.last_activity_at = payload.opened_at

    log = build_agent_log(
        agent=agent,
        event_type=LogEventType.COMMENT,
        summary=f"risk opened: {payload.title}",
        reported_by=payload.reported_by,
        report_source=payload.report_source,
        request_id=request_id,
        idempotency_key=payload.idempotency_key,
        occurred_at=payload.opened_at,
        detail_json={
            "risk_id": risk.id,
            "risk_type": payload.risk_type.value,
            "risk_level": payload.risk_level.value,
            "title": payload.title,
        },
    )
    db.add(log)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing_log = find_existing_agent_log(db, agent_id=agent.id, idempotency_key=payload.idempotency_key)
        if existing_log is not None and isinstance(existing_log.detail_json, dict) and existing_log.detail_json.get("risk_id"):
            existing_risk = db.get(RunRisk, existing_log.detail_json["risk_id"])
            if existing_risk is not None:
                return existing_risk
        raise
    db.refresh(risk)
    return risk


def resolve_agent_risk(
    db: Session,
    *,
    agent: RunAgent,
    risk: RunRisk,
    payload: AgentRiskResolve,
    request_id: str,
) -> RunRisk:
    existing_log = find_existing_agent_log(db, agent_id=agent.id, idempotency_key=payload.idempotency_key)
    if existing_log is not None:
        db.refresh(risk)
        return risk

    resolved_at = payload.resolved_at
    risk.status = payload.status
    risk.resolved_by = payload.resolved_by
    risk.resolved_at = resolved_at
    risk.duration_seconds_snapshot = int((_normalize_dt(resolved_at) - _normalize_dt(risk.opened_at)).total_seconds())

    db.flush()
    agent.risk_level = _recalculate_agent_risk_level(db, agent.id)
    agent.version_no = (agent.version_no or 1) + 1
    agent.last_update_at = resolved_at
    if agent.run is not None:
        agent.run.last_activity_at = resolved_at

    log = build_agent_log(
        agent=agent,
        event_type=LogEventType.COMMENT,
        summary=f"risk resolved: {risk.title}",
        reported_by=payload.resolved_by,
        report_source=payload.report_source,
        request_id=request_id,
        idempotency_key=payload.idempotency_key,
        occurred_at=resolved_at,
        detail_json={
            "risk_id": risk.id,
            "resolution_note": payload.resolution_note,
            "status": payload.status.value,
        },
    )
    db.add(log)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing_log = find_existing_agent_log(db, agent_id=agent.id, idempotency_key=payload.idempotency_key)
        if existing_log is not None:
            db.refresh(risk)
            return risk
        raise
    db.refresh(risk)
    return risk
