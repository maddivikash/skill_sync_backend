"""deadlines + reminder prefs: steps.due_date, users.email_reminders

Revision ID: d4sched01
Revises: c3prep01
Create Date: 2026-07-29

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4sched01"
down_revision: Union[str, None] = "c3prep01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("steps", sa.Column("due_date", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("email_reminders", sa.Boolean(),
                                     nullable=False, server_default=sa.true()))


def downgrade() -> None:
    op.drop_column("users", "email_reminders")
    op.drop_column("steps", "due_date")
