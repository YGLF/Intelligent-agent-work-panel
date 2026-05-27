"""create agent status tables

Revision ID: 0001_create_agent_status_tables
Revises:
Create Date: 2026-05-25 12:35:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0001_create_agent_status_tables"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_code", sa.String(length=64), nullable=False),
        sa.Column("run_name", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.Enum("codex", "manual", "system", name="runsourcetype", native_enum=False, length=32), nullable=False),
        sa.Column("status", sa.Enum("pending", "running", "waiting", "blocked", "completed", "failed", name="runstatus", native_enum=False, length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_runs")),
        sa.UniqueConstraint("run_code", name=op.f("uq_runs_run_code")),
    )
    op.create_index("idx_started_at", "runs", ["started_at"], unique=False)
    op.create_index("idx_status_last_activity_at", "runs", ["status", "last_activity_at"], unique=False)

    op.create_table(
        "run_agents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("agent_code", sa.String(length=64), nullable=False),
        sa.Column("agent_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=128), nullable=False),
        sa.Column("owner_scope", sa.String(length=128), nullable=True),
        sa.Column("status", sa.Enum("pending", "running", "waiting", "blocked", "completed", "failed", name="runstatus", native_enum=False, length=32), nullable=False),
        sa.Column("phase", sa.Enum("analysis", "design", "implementation", "test", "integration", name="agentphase", native_enum=False, length=32), nullable=True),
        sa.Column("progress_percent", sa.Integer(), nullable=False),
        sa.Column("current_task", sa.String(length=500), nullable=True),
        sa.Column("risk_level", sa.Enum("low", "medium", "high", name="risklevel", native_enum=False, length=32), nullable=False),
        sa.Column("blocking_reason", sa.Text(), nullable=True),
        sa.Column("depends_on_json", sa.Text(), nullable=True),
        sa.Column("handoff_to", sa.String(length=128), nullable=True),
        sa.Column("needs_input", sa.Boolean(), nullable=False),
        sa.Column("deliverable_summary", sa.Text(), nullable=True),
        sa.Column("codex_agent_type", sa.String(length=64), nullable=True),
        sa.Column("conversation_ref", sa.String(length=255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_update_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], name=op.f("fk_run_agents_run_id_runs")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_run_agents")),
        sa.UniqueConstraint("run_id", "agent_code", name="uk_run_agent"),
        sa.CheckConstraint("progress_percent >= 0 AND progress_percent <= 100", name="ck_run_agents_progress_percent_range"),
    )
    op.create_index("idx_run_last_update", "run_agents", ["run_id", "last_update_at"], unique=False)
    op.create_index("idx_run_owner_scope", "run_agents", ["run_id", "owner_scope"], unique=False)
    op.create_index("idx_run_phase", "run_agents", ["run_id", "phase"], unique=False)
    op.create_index("idx_run_risk", "run_agents", ["run_id", "risk_level"], unique=False)
    op.create_index("idx_run_status", "run_agents", ["run_id", "status"], unique=False)

    op.create_table(
        "run_agent_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.Enum("status_change", "phase_change", "progress_update", "blocking_update", "comment", name="logeventtype", native_enum=False, length=32), nullable=False),
        sa.Column("old_status", sa.Enum("pending", "running", "waiting", "blocked", "completed", "failed", name="runstatus", native_enum=False, length=32), nullable=True),
        sa.Column("new_status", sa.Enum("pending", "running", "waiting", "blocked", "completed", "failed", name="runstatus", native_enum=False, length=32), nullable=True),
        sa.Column("old_phase", sa.Enum("analysis", "design", "implementation", "test", "integration", name="agentphase", native_enum=False, length=32), nullable=True),
        sa.Column("new_phase", sa.Enum("analysis", "design", "implementation", "test", "integration", name="agentphase", native_enum=False, length=32), nullable=True),
        sa.Column("before_progress", sa.Integer(), nullable=True),
        sa.Column("after_progress", sa.Integer(), nullable=True),
        sa.Column("summary", sa.String(length=255), nullable=False),
        sa.Column("detail_json", sa.Text(), nullable=True),
        sa.Column("reported_by", sa.String(length=128), nullable=False),
        sa.Column("operator_type", sa.Enum("agent", "user", "system", name="operatortype", native_enum=False, length=32), nullable=False),
        sa.Column("report_source", sa.Enum("api", "reporter", "system", name="reportsource", native_enum=False, length=32), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("source_event_id", sa.String(length=128), nullable=True),
        sa.Column("trace_id", sa.String(length=128), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("server_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("server_processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result_status", sa.Enum("success", "rejected", "error", name="resultstatus", native_enum=False, length=32), nullable=False),
        sa.Column("result_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["run_agents.id"], name=op.f("fk_run_agent_logs_agent_id_run_agents")),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], name=op.f("fk_run_agent_logs_run_id_runs")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_run_agent_logs")),
    )
    op.create_index("idx_agent_occurred", "run_agent_logs", ["agent_id", "occurred_at"], unique=False)
    op.create_index("idx_event_type", "run_agent_logs", ["event_type", "occurred_at"], unique=False)
    op.create_index("idx_run_occurred", "run_agent_logs", ["run_id", "occurred_at"], unique=False)

    op.create_table(
        "run_agent_artifacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("artifact_type", sa.Enum("file", "link", "summary", name="artifacttype", native_enum=False, length=32), nullable=False),
        sa.Column("artifact_name", sa.String(length=255), nullable=False),
        sa.Column("artifact_uri", sa.String(length=1024), nullable=False),
        sa.Column("artifact_version", sa.String(length=64), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["run_agents.id"], name=op.f("fk_run_agent_artifacts_agent_id_run_agents")),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], name=op.f("fk_run_agent_artifacts_run_id_runs")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_run_agent_artifacts")),
    )
    op.create_index("idx_agent_created", "run_agent_artifacts", ["agent_id", "created_at"], unique=False)
    op.create_index("idx_run_type", "run_agent_artifacts", ["run_id", "artifact_type"], unique=False)

    op.create_table(
        "run_risks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=True),
        sa.Column("risk_type", sa.Enum("blocker", "dependency", "quality", "other", name="risktype", native_enum=False, length=32), nullable=False),
        sa.Column("risk_level", sa.Enum("low", "medium", "high", name="risklevel", native_enum=False, length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("suggested_action", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("open", "mitigated", "resolved", name="riskstatus", native_enum=False, length=32), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds_snapshot", sa.BigInteger(), nullable=True),
        sa.Column("reported_by", sa.String(length=128), nullable=False),
        sa.Column("resolved_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["run_agents.id"], name=op.f("fk_run_risks_agent_id_run_agents")),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], name=op.f("fk_run_risks_run_id_runs")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_run_risks")),
    )
    op.create_index("idx_agent_opened", "run_risks", ["agent_id", "opened_at"], unique=False)
    op.create_index("idx_run_open_risk", "run_risks", ["run_id", "status", "risk_level"], unique=False)
    op.create_index("idx_status_updated", "run_risks", ["status", "updated_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_status_updated", table_name="run_risks")
    op.drop_index("idx_run_open_risk", table_name="run_risks")
    op.drop_index("idx_agent_opened", table_name="run_risks")
    op.drop_table("run_risks")

    op.drop_index("idx_run_type", table_name="run_agent_artifacts")
    op.drop_index("idx_agent_created", table_name="run_agent_artifacts")
    op.drop_table("run_agent_artifacts")

    op.drop_index("idx_run_occurred", table_name="run_agent_logs")
    op.drop_index("idx_event_type", table_name="run_agent_logs")
    op.drop_index("idx_agent_occurred", table_name="run_agent_logs")
    op.drop_table("run_agent_logs")

    op.drop_index("idx_run_status", table_name="run_agents")
    op.drop_index("idx_run_risk", table_name="run_agents")
    op.drop_index("idx_run_phase", table_name="run_agents")
    op.drop_index("idx_run_owner_scope", table_name="run_agents")
    op.drop_index("idx_run_last_update", table_name="run_agents")
    op.drop_table("run_agents")

    op.drop_index("idx_status_last_activity_at", table_name="runs")
    op.drop_index("idx_started_at", table_name="runs")
    op.drop_table("runs")
