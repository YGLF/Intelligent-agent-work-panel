"""add log idempotency unique constraint

Revision ID: 0002_add_log_idempotency_unique_constraint
Revises: 0001_create_agent_status_tables
Create Date: 2026-05-26 15:10:00
"""

from collections.abc import Sequence

from alembic import op


revision: str = "0002_add_log_idempotency_unique_constraint"
down_revision: str | None = "0001_create_agent_status_tables"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("run_agent_logs") as batch_op:
        batch_op.create_unique_constraint(
            "uk_run_agent_logs_agent_id_idempotency_key",
            ["agent_id", "idempotency_key"],
        )


def downgrade() -> None:
    with op.batch_alter_table("run_agent_logs") as batch_op:
        batch_op.drop_constraint(
            "uk_run_agent_logs_agent_id_idempotency_key",
            type_="unique",
        )
