from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_api_token, require_read_access, require_request_id
from app.db import get_db
from app.models.run import Run
from app.schemas.common import ApiResponse
from app.schemas.read import RiskListRead, RunOverviewRead, TimelineRead
from app.schemas.run import RunCreate, RunRead
from app.services.audit import emit_rejected_request_audit
from app.services.read import get_run_overview, get_run_risks, get_run_timeline

router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


@router.post("", response_model=ApiResponse[RunRead], status_code=status.HTTP_201_CREATED)
def create_run(
    payload: RunCreate,
    response: Response,
    request_id: str = Depends(require_request_id),
    created_by: str = Depends(require_api_token),
    db: Session = Depends(get_db),
) -> ApiResponse[RunRead]:
    run = Run(
        run_code=payload.run_code,
        run_name=payload.run_name,
        source_type=payload.source_type,
        created_by=created_by,
    )
    db.add(run)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        emit_rejected_request_audit(
            action="create_run",
            request_id=request_id,
            actor=created_by,
            reason="run_code already exists",
            http_status=status.HTTP_409_CONFLICT,
            detail={
                "run_code": payload.run_code,
                "source_type": payload.source_type.value,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="run_code already exists",
        ) from exc

    db.refresh(run)
    response.headers["x-request-id"] = request_id

    return ApiResponse[RunRead](
        success=True,
        code="CREATED",
        message="run created",
        data=RunRead.model_validate(run),
        request_id=request_id,
    )


@router.get("/by-code/{run_code}", response_model=ApiResponse[RunRead])
def read_run_by_code(
    run_code: str,
    response: Response,
    request_id: str = Depends(require_request_id),
    created_by: str = Depends(require_api_token),
    db: Session = Depends(get_db),
) -> ApiResponse[RunRead]:
    run = db.query(Run).filter(Run.run_code == run_code).first()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")

    response.headers["x-request-id"] = request_id
    return ApiResponse[RunRead](
        success=True,
        code="OK",
        message="run retrieved",
        data=RunRead.model_validate(run),
        request_id=request_id,
    )


@router.get("/{run_id}/overview", response_model=ApiResponse[RunOverviewRead])
def read_run_overview(
    run_id: int,
    response: Response,
    request_id: str = Depends(require_request_id),
    created_by: str = Depends(require_read_access),
    db: Session = Depends(get_db),
) -> ApiResponse[RunOverviewRead]:
    overview = get_run_overview(db, run_id)
    if overview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")

    response.headers["x-request-id"] = request_id
    return ApiResponse[RunOverviewRead](
        success=True,
        code="OK",
        message="overview retrieved",
        data=overview,
        request_id=request_id,
    )


@router.get("/{run_id}/timeline", response_model=ApiResponse[TimelineRead])
def read_run_timeline(
    run_id: int,
    response: Response,
    request_id: str = Depends(require_request_id),
    created_by: str = Depends(require_read_access),
    db: Session = Depends(get_db),
) -> ApiResponse[TimelineRead]:
    run, timeline = get_run_timeline(db, run_id)
    if run is None or timeline is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")

    response.headers["x-request-id"] = request_id
    return ApiResponse[TimelineRead](
        success=True,
        code="OK",
        message="timeline retrieved",
        data=timeline,
        request_id=request_id,
    )


@router.get("/{run_id}/risks", response_model=ApiResponse[RiskListRead])
def read_run_risks(
    run_id: int,
    response: Response,
    request_id: str = Depends(require_request_id),
    created_by: str = Depends(require_read_access),
    db: Session = Depends(get_db),
) -> ApiResponse[RiskListRead]:
    run, risks = get_run_risks(db, run_id)
    if run is None or risks is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")

    response.headers["x-request-id"] = request_id
    return ApiResponse[RiskListRead](
        success=True,
        code="OK",
        message="risks retrieved",
        data=risks,
        request_id=request_id,
    )
