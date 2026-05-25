from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_api_token, require_request_id
from app.db import get_db
from app.models.run import Run
from app.schemas.common import ApiResponse
from app.schemas.run import RunCreate, RunRead

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
