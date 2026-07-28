"""job-prep: jd_text + readiness_base on goals, due_date on tasks

Revision ID: c3prep01
Revises: b1c2archive01
Create Date: 2026-07-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3prep01"
down_revision: Union[str, None] = "b1c2archive01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("goals", sa.Column("jd_text", sa.Text(), nullable=True))
    op.add_column("goals", sa.Column("readiness_base", sa.Integer(), nullable=True))
    op.add_column("tasks", sa.Column("due_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "due_date")
    op.drop_column("goals", "readiness_base")
    op.drop_column("goals", "jd_text")
