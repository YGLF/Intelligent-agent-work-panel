import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.agent import RunAgent
from app.models.enums import LogEventType, OperatorType, ReportSource, ResultStatus
from app.models.log import RunAgentLog

logger = logging.getLogger("app.audit")


def _normalize_report_source(report_source: str) -> ReportSource:
    value = report_source.strip().lower()
    if value in {source.value for source in ReportSource}:
        return ReportSource(value)
    return ReportSource.SYSTEM


def _redact_actor(actor: str | None) -> str:
    if not actor:
        return "unknown"
    if actor.startswith("token:"):
        return "token-authenticated-caller"
    return actor


def emit_rejected_request_audit(
    *,
    action: str,
    request_id: str | None,
    actor: str | None,
    reason: str,
    http_status: int,
    detail: dict | None = None,
) -> None:
    payload = {
        "event": "audit_rejected_request",
        "action": action,
        "request_id": request_id,
        "actor": _redact_actor(actor),
        "reason": reason,
        "http_status": http_status,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }
    if detail:
        payload["detail"] = detail
    logger.warning(json.dumps(payload, ensure_ascii=True, sort_keys=True))


def find_existing_agent_log(
    db: Session,
    *,
    agent_id: int,
    idempotency_key: str | None,
) -> RunAgentLog | None:
    if not idempotency_key:
        return None
    return db.query(RunAgentLog).filter(
        RunAgentLog.agent_id == agent_id,
        RunAgentLog.idempotency_key == idempotency_key,
    ).order_by(RunAgentLog.id.asc()).first()


def append_agent_audit_log(
    db: Session,
    *,
    agent: RunAgent,
    event_type: LogEventType,
    summary: str,
    reported_by: str,
    report_source: str,
    request_id: str | None,
    idempotency_key: str | None,
    occurred_at: datetime,
    old_status=None,
    new_status=None,
    old_phase=None,
    new_phase=None,
    before_progress: int | None = None,
    after_progress: int | None = None,
    detail_json: dict | list | None = None,
) -> RunAgentLog:
    log = build_agent_log(
        agent=agent,
        event_type=event_type,
        summary=summary,
        reported_by=reported_by,
        report_source=report_source,
        request_id=request_id,
        idempotency_key=idempotency_key,
        occurred_at=occurred_at,
        old_status=old_status,
        new_status=new_status,
        old_phase=old_phase,
        new_phase=new_phase,
        before_progress=before_progress,
        after_progress=after_progress,
        detail_json=detail_json,
    )
    db.add(log)
    return log


def build_agent_log(
    *,
    agent: RunAgent,
    event_type: LogEventType,
    summary: str,
    reported_by: str,
    report_source: str,
    request_id: str | None,
    idempotency_key: str | None,
    occurred_at: datetime,
    old_status=None,
    new_status=None,
    old_phase=None,
    new_phase=None,
    before_progress: int | None = None,
    after_progress: int | None = None,
    detail_json: dict | list | None = None,
) -> RunAgentLog:
    return RunAgentLog(
        run_id=agent.run_id,
        agent_id=agent.id,
        event_type=event_type,
        old_status=old_status,
        new_status=new_status,
        old_phase=old_phase,
        new_phase=new_phase,
        before_progress=before_progress,
        after_progress=after_progress,
        summary=summary,
        detail_json=detail_json,
        reported_by=reported_by,
        operator_type=OperatorType.AGENT,
        report_source=_normalize_report_source(report_source),
        request_id=request_id,
        idempotency_key=idempotency_key,
        source_event_id=None,
        trace_id=None,
        occurred_at=occurred_at,
        server_received_at=datetime.now(timezone.utc),
        server_processed_at=datetime.now(timezone.utc),
        result_status=ResultStatus.SUCCESS,
        result_message=None,
    )
