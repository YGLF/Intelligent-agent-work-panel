from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_api_token, require_request_id
from app.db import get_db
from app.models.agent import RunAgent
from app.models.run import Run
from app.schemas.agent import AgentRead, AgentRegister, AgentStatusUpdate
from app.schemas.common import ApiResponse
from app.services.agents import register_agent, update_agent_status

router = APIRouter(prefix="/api/v1/runs/{run_id}/agents", tags=["agents"])


@router.post("/register", response_model=ApiResponse[AgentRead], status_code=status.HTTP_201_CREATED)
def register_run_agent(
    run_id: int,
    payload: AgentRegister,
    response: Response,
    request_id: str = Depends(require_request_id),
    created_by: str = Depends(require_api_token),
    db: Session = Depends(get_db),
) -> ApiResponse[AgentRead]:
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")

    try:
        agent = register_agent(db, run, payload)
    except IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="agent_code already exists") from exc

    response.headers["x-request-id"] = request_id
    return ApiResponse[AgentRead](
        success=True,
        code="CREATED",
        message="agent registered",
        data=AgentRead.model_validate(agent),
        request_id=request_id,
    )


@router.post("/{agent_id}/status", response_model=ApiResponse[AgentRead])
def update_run_agent_status(
    run_id: int,
    agent_id: int,
    payload: AgentStatusUpdate,
    response: Response,
    request_id: str = Depends(require_request_id),
    created_by: str = Depends(require_api_token),
    db: Session = Depends(get_db),
) -> ApiResponse[AgentRead]:
    agent = db.get(RunAgent, agent_id)
    if agent is None or agent.run_id != run_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agent not found")

    updated = update_agent_status(db, agent=agent, payload=payload)
    response.headers["x-request-id"] = request_id
    return ApiResponse[AgentRead](
        success=True,
        code="OK",
        message="agent status updated",
        data=AgentRead.model_validate(updated),
        request_id=request_id,
    )
