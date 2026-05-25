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


def test_settings_default_database_url_is_explicitly_local_only():
    settings = Settings(_env_file=None)

    assert settings.database_url == "sqlite:///./local_dev_agent_status_panel.db"


def test_settings_rejects_implicit_local_sqlite_outside_local_modes():
    with pytest.raises(ValueError, match="APP_ENV"):
        Settings(app_env="prod", _env_file=None)


def test_create_run_requires_token_and_returns_run_code(client):
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
    assert payload["data"]["run_code"] == "run-001"
