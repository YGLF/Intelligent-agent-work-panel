from fastapi import FastAPI


SERVICE_NAME = "codex-agent-status-panel"
SERVICE_VERSION = "0.1.0"


def create_app() -> FastAPI:
    app = FastAPI(title=SERVICE_NAME, version=SERVICE_VERSION)

    @app.get("/health")
    def health() -> dict:
        return {
            "success": True,
            "code": "OK",
            "message": "service healthy",
            "data": {
                "service": SERVICE_NAME,
                "version": SERVICE_VERSION,
            },
        }

    return app


app = create_app()
