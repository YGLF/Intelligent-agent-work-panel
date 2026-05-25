from fastapi import FastAPI

from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version)

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

    return app


app = create_app()
