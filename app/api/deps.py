from fastapi import Depends, Header, HTTPException, status

from app.config import Settings, get_settings

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
