"""add agent hierarchy fields

Revision ID: 0004_add_agent_hierarchy_fields
Revises: 0003_add_artifact_idempotency_unique_constraint
Create Date: 2026-05-27 15:45:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0004_add_agent_hierarchy_fields"
down_revision: str | None = "0003_add_artifact_idempotency_unique_constraint"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("run_agents") as batch_op:
        batch_op.add_column(sa.Column("is_main_agent", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("parent_agent_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_run_agents_parent_agent_id_run_agents",
            "run_agents",
            ["parent_agent_id"],
            ["id"],
        )
        batch_op.create_index("idx_run_parent_agent", ["run_id", "parent_agent_id"], unique=False)
        batch_op.create_index("idx_run_is_main_agent", ["run_id", "is_main_agent"], unique=False)

    op.execute(
        sa.text(
            """
            UPDATE run_agents
            SET is_main_agent = 1
            WHERE LOWER(COALESCE(codex_agent_type, '')) IN ('main', 'orchestrator')
            """
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("run_agents") as batch_op:
        batch_op.drop_index("idx_run_is_main_agent")
        batch_op.drop_index("idx_run_parent_agent")
        batch_op.drop_constraint("fk_run_agents_parent_agent_id_run_agents", type_="foreignkey")
        batch_op.drop_column("parent_agent_id")
        batch_op.drop_column("is_main_agent")
