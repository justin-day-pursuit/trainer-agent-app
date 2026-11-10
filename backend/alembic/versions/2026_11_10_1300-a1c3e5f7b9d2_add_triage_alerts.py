"""add_triage_alerts

Revision ID: a1c3e5f7b9d2
Revises: f575ae68b0f2
Create Date: 2026-11-10 13:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1c3e5f7b9d2"
down_revision: Union[str, None] = "f575ae68b0f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "triage_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("alert_key", sa.String(length=100), nullable=False),
        sa.Column("draft_message", sa.Text(), nullable=False),
        sa.Column("dismissed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["client_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", "alert_key", name="uq_triage_client_alert"),
    )
    op.create_index(op.f("ix_triage_alerts_id"), "triage_alerts", ["id"], unique=False)
    op.create_index(op.f("ix_triage_alerts_client_id"), "triage_alerts", ["client_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_triage_alerts_client_id"), table_name="triage_alerts")
    op.drop_index(op.f("ix_triage_alerts_id"), table_name="triage_alerts")
    op.drop_table("triage_alerts")
