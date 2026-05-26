from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ArtifactType


class AgentArtifactCreate(BaseModel):
    artifact_type: ArtifactType
    artifact_name: str = Field(min_length=1, max_length=255)
    artifact_uri: str = Field(min_length=1, max_length=1024)
    artifact_version: str | None = Field(default=None, max_length=64)
    summary: str | None = None
    idempotency_key: str | None = Field(default=None, max_length=128)


class AgentArtifactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    agent_id: int
    artifact_type: ArtifactType
    artifact_name: str
    artifact_uri: str
    artifact_version: str | None
    summary: str | None
    created_by: str
    created_at: datetime
