import pytest

from app.config import Settings
from app.db import Base
from app.models import agent, artifact, log, risk, run  # noqa: F401


def test_metadata_contains_expected_tables():
    table_names = set(Base.metadata.tables)

    assert table_names == {
        "runs",
        "run_agents",
        "run_agent_logs",
        "run_agent_artifacts",
        "run_risks",
    }


def test_run_agents_metadata_contains_key_constraints():
    run_agents = Base.metadata.tables["run_agents"]

    unique_constraints = {
        tuple(column.name for column in constraint.columns): constraint.name
        for constraint in run_agents.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    check_constraints = {constraint.name for constraint in run_agents.constraints if constraint.__class__.__name__ == "CheckConstraint"}

    assert unique_constraints[("run_id", "agent_code")] == "uk_run_agent"
    assert "ck_run_agents_progress_percent_range" in check_constraints


def test_run_agent_logs_metadata_contains_idempotency_unique_constraint():
    run_agent_logs = Base.metadata.tables["run_agent_logs"]

    unique_constraints = {
        tuple(column.name for column in constraint.columns): constraint.name
        for constraint in run_agent_logs.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }

    assert unique_constraints[("agent_id", "idempotency_key")] == "uk_run_agent_logs_agent_id_idempotency_key"


def test_settings_default_database_url_is_explicitly_local_only():
    settings = Settings(_env_file=None)

    assert settings.database_url == "sqlite:///./local_dev_agent_status_panel.db"


def test_settings_rejects_implicit_local_sqlite_outside_local_modes():
    with pytest.raises(ValueError, match="APP_ENV"):
        Settings(app_env="prod", _env_file=None)


def test_settings_rejects_default_api_token_in_prod():
    with pytest.raises(ValueError, match="API_TOKEN"):
        Settings(
            app_env="prod",
            database_url="postgresql://example.invalid/task3",
            api_token="dev-token",
            _env_file=None,
        )


def test_settings_rejects_default_api_token_for_non_local_database_without_explicit_local_mode():
    with pytest.raises(ValueError, match="API_TOKEN"):
        Settings(
            database_url="postgresql://example.invalid/task3",
            api_token="dev-token",
            _env_file=None,
        )


def test_settings_accepts_custom_api_token_in_prod():
    settings = Settings(
        app_env="prod",
        database_url="postgresql://example.invalid/task3",
        api_token="custom-token",
        _env_file=None,
    )

    assert settings.api_token == "custom-token"


def test_create_run_rejects_missing_token(client):
    response = client.post(
        "/api/v1/runs",
        headers={"x-request-id": "req-000"},
        json={
            "run_code": "run-000",
            "run_name": "Missing token run",
            "source_type": "codex",
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "x-api-token header is required"}


def test_create_run_rejects_invalid_token(client):
    response = client.post(
        "/api/v1/runs",
        headers={"x-api-token": "wrong-token", "x-request-id": "req-401"},
        json={
            "run_code": "run-401",
            "run_name": "Invalid token run",
            "source_type": "codex",
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "x-api-token header is invalid"}


@pytest.mark.parametrize(
    ("headers", "expected_status", "expected_detail"),
    [
        ({"x-api-token": "dev-token"}, 400, "x-request-id header is required"),
        ({"x-api-token": "dev-token", "x-request-id": "   "}, 400, "x-request-id header must not be blank"),
    ],
)
def test_create_run_rejects_missing_or_blank_request_id(client, headers, expected_status, expected_detail):
    response = client.post(
        "/api/v1/runs",
        headers=headers,
        json={
            "run_code": "run-req",
            "run_name": "Request id validation run",
            "source_type": "codex",
        },
    )

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}


def test_create_run_returns_run_code_when_token_provided(client):
    response = client.post(
        "/api/v1/runs",
        headers={"x-api-token": "dev-token", "x-request-id": "req-001"},
        json={
            "run_code": "run-001",
            "run_name": "Codex coordination run",
            "source_type": "codex",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["success"] is True
    assert payload["code"] == "CREATED"
    assert payload["message"] == "run created"
    assert payload["request_id"] == "req-001"
    assert response.headers["x-request-id"] == "req-001"
    assert payload["data"]["id"] > 0
    assert payload["data"]["status"] == "pending"
    assert payload["data"]["created_by"] == "token:dev-token"
    assert payload["data"]["run_code"] == "run-001"


def test_create_run_rejects_duplicate_run_code(client):
    first_response = client.post(
        "/api/v1/runs",
        headers={"x-api-token": "dev-token", "x-request-id": "req-dup-1"},
        json={
            "run_code": "run-dup",
            "run_name": "First duplicate run",
            "source_type": "codex",
        },
    )
    second_response = client.post(
        "/api/v1/runs",
        headers={"x-api-token": "dev-token", "x-request-id": "req-dup-2"},
        json={
            "run_code": "run-dup",
            "run_name": "Second duplicate run",
            "source_type": "codex",
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json() == {"detail": "run_code already exists"}


def test_create_run_duplicate_emits_rejection_audit_log(client, caplog):
    with caplog.at_level("WARNING", logger="app.audit"):
        first_response = client.post(
            "/api/v1/runs",
            headers={"x-api-token": "dev-token", "x-request-id": "req-dup-audit-1"},
            json={
                "run_code": "run-dup-audit",
                "run_name": "First duplicate audit run",
                "source_type": "codex",
            },
        )
        second_response = client.post(
            "/api/v1/runs",
            headers={"x-api-token": "dev-token", "x-request-id": "req-dup-audit-2"},
            json={
                "run_code": "run-dup-audit",
                "run_name": "Second duplicate audit run",
                "source_type": "codex",
            },
        )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert '"action": "create_run"' in caplog.text
    assert '"request_id": "req-dup-audit-2"' in caplog.text
    assert '"reason": "run_code already exists"' in caplog.text
    assert '"run_code": "run-dup-audit"' in caplog.text
    assert '"actor": "token-authenticated-caller"' in caplog.text
