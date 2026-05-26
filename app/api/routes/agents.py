from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_api_token, require_read_access, require_request_id
from app.db import get_db
from app.models.agent import RunAgent
from app.models.run import Run
from app.schemas.artifact import AgentArtifactCreate, AgentArtifactRead
from app.schemas.agent import AgentRead, AgentRegister, AgentStatusUpdate
from app.schemas.common import ApiResponse
from app.schemas.log import AgentLogCreate, AgentLogRead
from app.schemas.risk import AgentRiskCreate, AgentRiskResolve
from app.schemas.read import AgentDetailRead, AgentListRead
from app.services.activity import append_agent_log, register_agent_artifact
from app.services.agents import register_agent, update_agent_status
from app.services.audit import emit_rejected_request_audit
from app.services.risks import open_agent_risk, resolve_agent_risk
from app.services.read import get_agent_detail, list_run_agents
from app.schemas.read import RiskItemRead
from app.models.risk import RunRisk

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
        emit_rejected_request_audit(
            action="register_run_agent",
            request_id=request_id,
            actor=created_by,
            reason="run not found",
            http_status=status.HTTP_404_NOT_FOUND,
            detail={
                "run_id": run_id,
                "agent_code": payload.agent_code,
            },
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")

    try:
        agent = register_agent(db, run, payload)
    except IntegrityError as exc:
        emit_rejected_request_audit(
            action="register_run_agent",
            request_id=request_id,
            actor=created_by,
            reason="agent_code already exists",
            http_status=status.HTTP_409_CONFLICT,
            detail={
                "run_id": run_id,
                "agent_code": payload.agent_code,
            },
        )
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

    updated = update_agent_status(db, agent=agent, payload=payload, audit_request_id=request_id)
    response.headers["x-request-id"] = request_id
    return ApiResponse[AgentRead](
        success=True,
        code="OK",
        message="agent status updated",
        data=AgentRead.model_validate(updated),
        request_id=request_id,
    )


@router.get("", response_model=ApiResponse[AgentListRead])
def list_agents(
    run_id: int,
    response: Response,
    status_filter: str | None = None,
    phase: str | None = None,
    owner_scope: str | None = None,
    risk_level: str | None = None,
    blocked_only: bool = False,
    request_id: str = Depends(require_request_id),
    created_by: str = Depends(require_read_access),
    db: Session = Depends(get_db),
) -> ApiResponse[AgentListRead]:
    run, payload = list_run_agents(
        db,
        run_id,
        status=status_filter,
        phase=phase,
        owner_scope=owner_scope,
        risk_level=risk_level,
        blocked_only=blocked_only,
    )
    if run is None or payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")

    response.headers["x-request-id"] = request_id
    return ApiResponse[AgentListRead](
        success=True,
        code="OK",
        message="agents retrieved",
        data=payload,
        request_id=request_id,
    )


@router.get("/by-code/{agent_code}", response_model=ApiResponse[AgentRead])
def get_agent_by_code(
    run_id: int,
    agent_code: str,
    response: Response,
    request_id: str = Depends(require_request_id),
    created_by: str = Depends(require_api_token),
    db: Session = Depends(get_db),
) -> ApiResponse[AgentRead]:
    agent = db.query(RunAgent).filter(RunAgent.run_id == run_id, RunAgent.agent_code == agent_code).first()
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agent not found")

    response.headers["x-request-id"] = request_id
    return ApiResponse[AgentRead](
        success=True,
        code="OK",
        message="agent retrieved",
        data=AgentRead.model_validate(agent),
        request_id=request_id,
    )


@router.get("/{agent_id}", response_model=ApiResponse[AgentDetailRead])
def get_agent(
    run_id: int,
    agent_id: int,
    response: Response,
    request_id: str = Depends(require_request_id),
    created_by: str = Depends(require_read_access),
    db: Session = Depends(get_db),
) -> ApiResponse[AgentDetailRead]:
    agent = get_agent_detail(db, run_id, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agent not found")

    response.headers["x-request-id"] = request_id
    return ApiResponse[AgentDetailRead](
        success=True,
        code="OK",
        message="agent retrieved",
        data=agent,
        request_id=request_id,
    )


@router.post("/{agent_id}/log", response_model=ApiResponse[AgentLogRead], status_code=status.HTTP_201_CREATED)
def append_log(
    run_id: int,
    agent_id: int,
    payload: AgentLogCreate,
    response: Response,
    request_id: str = Depends(require_request_id),
    created_by: str = Depends(require_api_token),
    db: Session = Depends(get_db),
) -> ApiResponse[AgentLogRead]:
    agent = db.get(RunAgent, agent_id)
    if agent is None or agent.run_id != run_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agent not found")

    log = append_agent_log(db, agent=agent, payload=payload, request_id=request_id)
    response.headers["x-request-id"] = request_id
    return ApiResponse[AgentLogRead](
        success=True,
        code="CREATED",
        message="agent log appended",
        data=AgentLogRead.model_validate(log),
        request_id=request_id,
    )


@router.post("/{agent_id}/artifact", response_model=ApiResponse[AgentArtifactRead], status_code=status.HTTP_201_CREATED)
def add_artifact(
    run_id: int,
    agent_id: int,
    payload: AgentArtifactCreate,
    response: Response,
    request_id: str = Depends(require_request_id),
    created_by: str = Depends(require_api_token),
    db: Session = Depends(get_db),
) -> ApiResponse[AgentArtifactRead]:
    agent = db.get(RunAgent, agent_id)
    if agent is None or agent.run_id != run_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agent not found")

    artifact = register_agent_artifact(
        db,
        agent=agent,
        payload=payload,
        created_by=created_by,
        request_id=request_id,
    )
    response.headers["x-request-id"] = request_id
    return ApiResponse[AgentArtifactRead](
        success=True,
        code="CREATED",
        message="agent artifact registered",
        data=AgentArtifactRead.model_validate(artifact),
        request_id=request_id,
    )


@router.post("/{agent_id}/risk", response_model=ApiResponse[RiskItemRead], status_code=status.HTTP_201_CREATED)
def add_risk(
    run_id: int,
    agent_id: int,
    payload: AgentRiskCreate,
    response: Response,
    request_id: str = Depends(require_request_id),
    created_by: str = Depends(require_api_token),
    db: Session = Depends(get_db),
) -> ApiResponse[RiskItemRead]:
    agent = db.get(RunAgent, agent_id)
    if agent is None or agent.run_id != run_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agent not found")

    risk = open_agent_risk(db, agent=agent, payload=payload, request_id=request_id)
    response.headers["x-request-id"] = request_id
    return ApiResponse[RiskItemRead](
        success=True,
        code="CREATED",
        message="risk opened",
        data=RiskItemRead.model_validate(risk),
        request_id=request_id,
    )


@router.post("/{agent_id}/risks/{risk_id}/resolve", response_model=ApiResponse[RiskItemRead])
def resolve_risk(
    run_id: int,
    agent_id: int,
    risk_id: int,
    payload: AgentRiskResolve,
    response: Response,
    request_id: str = Depends(require_request_id),
    created_by: str = Depends(require_api_token),
    db: Session = Depends(get_db),
) -> ApiResponse[RiskItemRead]:
    agent = db.get(RunAgent, agent_id)
    if agent is None or agent.run_id != run_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agent not found")

    risk = db.get(RunRisk, risk_id)
    if risk is None or risk.run_id != run_id or risk.agent_id != agent_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="risk not found")

    resolved = resolve_agent_risk(db, agent=agent, risk=risk, payload=payload, request_id=request_id)
    response.headers["x-request-id"] = request_id
    return ApiResponse[RiskItemRead](
        success=True,
        code="OK",
        message="risk resolved",
        data=RiskItemRead.model_validate(resolved),
        request_id=request_id,
    )
