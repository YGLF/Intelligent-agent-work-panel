from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RunSourceType, RunStatus


class RunCreate(BaseModel):
    run_code: str = Field(min_length=1, max_length=64)
    run_name: str = Field(min_length=1, max_length=255)
    source_type: RunSourceType


class RunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_code: str
    run_name: str
    source_type: RunSourceType
    status: RunStatus
    created_by: str
