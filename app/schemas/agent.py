from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AgentPhase, RiskLevel, RunStatus


class AgentRegister(BaseModel):
    agent_code: str = Field(min_length=1, max_length=64)
    agent_name: str = Field(min_length=1, max_length=255)
    role: str = Field(min_length=1, max_length=128)
    owner_scope: str | None = Field(default=None, max_length=128)


class AgentStatusUpdate(BaseModel):
    agent_name: str = Field(min_length=1, max_length=255)
    status: RunStatus
    phase: AgentPhase | None = None
    progress_percent: int = Field(ge=0, le=100)
    current_task: str | None = Field(default=None, max_length=500)
    blocking_reason: str | None = None
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
    last_update_at: datetime | None
    version_no: int
