"""add is_archived to goals

Revision ID: b1c2archive01
Revises: 940f61d616da
Create Date: 2026-07-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1c2archive01"
down_revision: Union[str, None] = "940f61d616da"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "goals",
        sa.Column("is_archived", sa.Boolean(), nullable=False,
                  server_default=sa.false()),
    )
    op.create_index("ix_goals_is_archived", "goals", ["is_archived"])


def downgrade() -> None:
    op.drop_index("ix_goals_is_archived", table_name="goals")
    op.drop_column("goals", "is_archived")
