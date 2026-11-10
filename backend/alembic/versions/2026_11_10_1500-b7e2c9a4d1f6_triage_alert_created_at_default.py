"""triage_alert_created_at_default

Revision ID: b7e2c9a4d1f6
Revises: a1c3e5f7b9d2
Create Date: 2026-11-10 15:00:00

The live database already applied a1c3e5f7b9d2 before created_at had a
default. Fresh databases get the default from that edited create. This
revision sets the same default on the database that is already running.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "b7e2c9a4d1f6"
down_revision: Union[str, None] = "a1c3e5f7b9d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Gives triage_alerts.created_at a timestamp when an insert omits one.

    This is for the live database that already created the table. A new
    database gets the same default from the earlier revision. Maintainers:
    leave this as a default change only. Do not rebuild the table.
    """
    op.execute("ALTER TABLE triage_alerts ALTER COLUMN created_at SET DEFAULT now()")


def downgrade() -> None:
    """Removes the timestamp default added for the live database.

    The column stays. Inserts that omit created_at would then need the
    application to supply the value again.
    """
    op.execute("ALTER TABLE triage_alerts ALTER COLUMN created_at DROP DEFAULT")
