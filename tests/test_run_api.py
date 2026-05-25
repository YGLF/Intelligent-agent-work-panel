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
