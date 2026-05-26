from fastapi import Depends, Header, HTTPException, Path, Request, status

from app.config import Settings, get_settings
from app.security.dashboard import DASHBOARD_SESSION_COOKIE_NAME, verify_dashboard_token

def require_request_id(x_request_id: str | None = Header(default=None, alias="x-request-id")) -> str:
    if x_request_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="x-request-id header is required",
        )

    request_id = x_request_id.strip()
    if not request_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="x-request-id header must not be blank",
        )

    return request_id


def require_api_token(
    x_api_token: str | None = Header(default=None, alias="x-api-token"),
    settings: Settings = Depends(get_settings),
) -> str:
    if x_api_token is None or not x_api_token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="x-api-token header is required",
        )

    if x_api_token != settings.api_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="x-api-token header is invalid",
        )

    return f"token:{settings.api_token}"


def require_read_access(
    request: Request,
    run_id: int = Path(...),
    x_api_token: str | None = Header(default=None, alias="x-api-token"),
    x_dashboard_token: str | None = Header(default=None, alias="x-dashboard-token"),
    settings: Settings = Depends(get_settings),
) -> str:
    dashboard_session_token = request.cookies.get(DASHBOARD_SESSION_COOKIE_NAME)
    if dashboard_session_token:
        if verify_dashboard_token(token=dashboard_session_token, run_id=run_id, secret=settings.api_token):
            return "dashboard-session"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="dashboard session cookie is invalid",
        )

    if x_api_token is not None and x_api_token.strip():
        if x_api_token != settings.api_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="x-api-token header is invalid",
            )
        return f"token:{settings.api_token}"

    if x_dashboard_token is not None and x_dashboard_token.strip():
        if verify_dashboard_token(token=x_dashboard_token, run_id=run_id, secret=settings.api_token):
            return "dashboard-read-token"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="x-dashboard-token header is invalid",
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="read access token is required",
    )
