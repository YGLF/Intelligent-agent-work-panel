from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.deps import require_api_token, require_request_id
from app.api.routes.agents import router as agents_router
from app.api.routes.runs import router as runs_router
from app.config import get_settings
from app.db import get_db
from app.models.run import Run
from app.security.dashboard import DASHBOARD_SESSION_COOKIE_NAME, create_dashboard_token, verify_dashboard_token
from app.schemas.common import ApiResponse

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _set_dashboard_session_cookie(response: Response, token: str, max_age: int, secure: bool) -> None:
    response.set_cookie(
        key=DASHBOARD_SESSION_COOKIE_NAME,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

    @app.get("/health")
    def health() -> dict:
        return {
            "success": True,
            "code": "OK",
            "message": "service healthy",
            "data": {
                "service": settings.app_name,
                "version": settings.app_version,
            },
        }

    @app.get("/runs/{run_id}/dashboard-token")
    def dashboard_token(
        run_id: int,
        response: Response,
        request_id: str = Depends(require_request_id),
        created_by: str = Depends(require_api_token),
        db=Depends(get_db),
    ) -> ApiResponse[dict[str, str | int]]:
        run = db.get(Run, run_id)
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
        token = create_dashboard_token(
            run_id=run_id,
            secret=settings.api_token,
            ttl_seconds=settings.dashboard_token_ttl_seconds,
        )
        _set_dashboard_session_cookie(
            response,
            token,
            max_age=settings.dashboard_token_ttl_seconds,
            secure=settings.app_env == "prod",
        )
        response.headers["x-request-id"] = request_id
        return ApiResponse[dict[str, str | int]](
            success=True,
            code="OK",
            message="dashboard token issued",
            data={"access_token": token, "expires_in": settings.dashboard_token_ttl_seconds},
            request_id=request_id,
        )

    @app.get("/runs/{run_id}/dashboard", response_class=HTMLResponse)
    def dashboard(
        request: Request,
        response: Response,
        run_id: int,
        access_token: str | None = Query(default=None),
        x_dashboard_token: str | None = Header(default=None, alias="x-dashboard-token"),
        db=Depends(get_db),
    ):
        dashboard_token_value = (
            request.cookies.get(DASHBOARD_SESSION_COOKIE_NAME)
            or access_token
            or x_dashboard_token
        )
        if not dashboard_token_value or not verify_dashboard_token(
            token=dashboard_token_value,
            run_id=run_id,
            secret=settings.api_token,
        ):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="dashboard access token is required")

        run = db.get(Run, run_id)
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
        template_response = templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "run_id": run_id,
            },
        )
        if dashboard_token_value != request.cookies.get(DASHBOARD_SESSION_COOKIE_NAME):
            _set_dashboard_session_cookie(
                template_response,
                dashboard_token_value,
                max_age=settings.dashboard_token_ttl_seconds,
                secure=settings.app_env == "prod",
            )
        return template_response

    app.include_router(runs_router)
    app.include_router(agents_router)

    return app


app = create_app()
