from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.enums import RiskLevel, RiskStatus, RiskType


class AgentRiskCreate(BaseModel):
    risk_type: RiskType
    risk_level: RiskLevel
    title: str = Field(min_length=1, max_length=255)
    reason: str = Field(min_length=1)
    suggested_action: str | None = None
    opened_at: datetime
    reported_by: str = Field(min_length=1, max_length=128)
    report_source: str = Field(min_length=1, max_length=64)
    idempotency_key: str | None = Field(default=None, max_length=128)


class AgentRiskResolve(BaseModel):
    status: RiskStatus
    resolved_at: datetime
    resolved_by: str = Field(min_length=1, max_length=128)
    resolution_note: str | None = None
    report_source: str = Field(min_length=1, max_length=64)
    idempotency_key: str | None = Field(default=None, max_length=128)

    @field_validator("status")
    @classmethod
    def validate_resolution_status(cls, value: RiskStatus) -> RiskStatus:
        if value == RiskStatus.OPEN:
            raise ValueError("resolution status must be mitigated or resolved")
        return value
