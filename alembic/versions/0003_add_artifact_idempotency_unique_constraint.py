"""add artifact idempotency unique constraint

Revision ID: 0003_add_artifact_idempotency_unique_constraint
Revises: 0002_add_log_idempotency_unique_constraint
Create Date: 2026-05-26 16:10:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0003_add_artifact_idempotency_unique_constraint"
down_revision: str | None = "0002_add_log_idempotency_unique_constraint"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("run_agent_artifacts") as batch_op:
        batch_op.add_column(sa.Column("idempotency_key", sa.String(length=128), nullable=True))
        batch_op.create_unique_constraint(
            "uk_run_agent_artifacts_agent_id_idempotency_key",
            ["agent_id", "idempotency_key"],
        )


def downgrade() -> None:
    with op.batch_alter_table("run_agent_artifacts") as batch_op:
        batch_op.drop_constraint(
            "uk_run_agent_artifacts_agent_id_idempotency_key",
            type_="unique",
        )
        batch_op.drop_column("idempotency_key")
