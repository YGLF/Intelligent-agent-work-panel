from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AgentPhase, RiskLevel, RunStatus


class AgentRegister(BaseModel):
    agent_code: str = Field(min_length=1, max_length=64)
    agent_name: str = Field(min_length=1, max_length=255)
    role: str = Field(min_length=1, max_length=128)
    owner_scope: str | None = Field(default=None, max_length=128)
    codex_agent_type: str | None = Field(default=None, max_length=64)
    model_name: str | None = Field(default=None, max_length=128)
    model_tier: str | None = Field(default=None, max_length=64)
    is_main_agent: bool = False
    parent_agent_id: int | None = None
    conversation_ref: str | None = Field(default=None, max_length=255)


class AgentStatusUpdate(BaseModel):
    agent_name: str = Field(min_length=1, max_length=255)
    status: RunStatus
    phase: AgentPhase | None = None
    progress_percent: int = Field(ge=0, le=100)
    current_task: str | None = Field(default=None, max_length=500)
    blocking_reason: str | None = None
    depends_on: list[str] | None = None
    handoff_to: str | None = Field(default=None, max_length=128)
    needs_input: bool | None = None
    deliverable_summary: str | None = None
    codex_agent_type: str | None = Field(default=None, max_length=64)
    model_name: str | None = Field(default=None, max_length=128)
    model_tier: str | None = Field(default=None, max_length=64)
    is_main_agent: bool | None = None
    parent_agent_id: int | None = None
    conversation_ref: str | None = Field(default=None, max_length=255)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    last_heartbeat_at: datetime | None = None
    ready_for_integration: bool | None = None
    risk_level: RiskLevel
    reported_at: datetime
    last_update_at: datetime
    reported_by: str = Field(min_length=1, max_length=128)
    report_source: str = Field(min_length=1, max_length=64)
    request_id: str | None = Field(default=None, max_length=64)
    idempotency_key: str | None = Field(default=None, max_length=128)


class AgentRead(BaseModel):
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
    codex_agent_type: str | None
    model_name: str | None
    model_tier: str | None
    is_main_agent: bool
    parent_agent_id: int | None
    conversation_ref: str | None
    last_update_at: datetime | None
    version_no: int
