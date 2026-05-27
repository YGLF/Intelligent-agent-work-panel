"""add agent model fields

Revision ID: 0005_add_agent_model_fields
Revises: 0004_add_agent_hierarchy_fields
Create Date: 2026-05-27 16:10:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0005_add_agent_model_fields"
down_revision: str | None = "0004_add_agent_hierarchy_fields"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("run_agents") as batch_op:
        batch_op.add_column(sa.Column("model_name", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("model_tier", sa.String(length=64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("run_agents") as batch_op:
        batch_op.drop_column("model_tier")
        batch_op.drop_column("model_name")
