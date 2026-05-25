# Codex Agent Status Panel

Conservative FastAPI bootstrap for the Python status panel service.

## Quick start

1. Create and activate a Python 3.12 virtual environment.
2. Install dependencies with `.\.venv\Scripts\python.exe -m pip install -e .[dev]`.
3. Create `.env` from the example with `Copy-Item .env.example .env`.
4. Start the service with `.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload`.
5. Run the bootstrap verification with `.\.venv\Scripts\pytest.exe tests/test_health_and_bootstrap.py::test_health_endpoint_returns_service_metadata -v`.
