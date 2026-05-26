from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import AgentPhase, LogEventType, ReportSource, ResultStatus, RiskLevel, RiskStatus, RiskType, RunSourceType, RunStatus


class RunOverviewRead(BaseModel):
    run_id: int
    run_code: str
    run_name: str
    source_type: RunSourceType
    run_status: RunStatus
    total_agents: int
    running_count: int
    completed_count: int
    blocked_count: int
    failed_count: int
    phase_distribution: dict[str, int]
    overall_progress: int
    active_updates_last_1h: int
    last_active_at: datetime | None
    stale_hint: str | None = None


class AgentListItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    agent_code: str
    agent_name: str
    role: str
    owner_scope: str | None
    status: RunStatus
    phase: AgentPhase | None
    progress_percent: int
    current_task: str | None
    risk_level: RiskLevel
    blocking_reason: str | None
    handoff_to: str | None
    needs_input: bool
    codex_agent_type: str | None
    deliverable_summary: str | None
    conversation_ref: str | None
    last_update_at: datetime | None
    last_heartbeat_at: datetime | None
    version_no: int


class AgentDetailRead(AgentListItemRead):
    depends_on: list[str] | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class AgentListRead(BaseModel):
    items: list[AgentListItemRead]
    has_more: bool = False
    next_cursor: str | None = None
    next_updated_since: datetime | None = None


class TimelineItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    agent_id: int
    event_type: LogEventType
    old_status: RunStatus | None
    new_status: RunStatus | None
    old_phase: AgentPhase | None
    new_phase: AgentPhase | None
    before_progress: int | None
    after_progress: int | None
    summary: str
    reported_by: str
    report_source: ReportSource
    request_id: str | None
    occurred_at: datetime
    result_status: ResultStatus


class TimelineRead(BaseModel):
    items: list[TimelineItemRead]
    has_more: bool = False
    next_cursor: str | None = None
    next_updated_since: datetime | None = None


class RiskItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    agent_id: int | None
    risk_type: RiskType
    risk_level: RiskLevel
    title: str
    reason: str
    suggested_action: str | None
    status: RiskStatus
    opened_at: datetime
    resolved_at: datetime | None
    duration_seconds_snapshot: int | None
    reported_by: str
    resolved_by: str | None
    updated_at: datetime


class RiskListRead(BaseModel):
    items: list[RiskItemRead]
    has_more: bool = False
    next_cursor: str | None = None
    next_updated_since: datetime | None = None
