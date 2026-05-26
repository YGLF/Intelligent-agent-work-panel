from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import LogEventType, ReportSource


class AgentLogCreate(BaseModel):
    event_type: LogEventType
    summary: str = Field(min_length=1, max_length=255)
    detail_json: dict | list | None = None
    reported_by: str = Field(min_length=1, max_length=128)
    report_source: str = Field(min_length=1, max_length=64)
    occurred_at: datetime
    idempotency_key: str | None = Field(default=None, max_length=128)


class AgentLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    agent_id: int
    event_type: LogEventType
    summary: str
    detail_json: dict | list | None
    reported_by: str
    report_source: ReportSource
    request_id: str | None
    occurred_at: datetime
