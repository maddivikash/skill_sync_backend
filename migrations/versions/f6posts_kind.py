"""posts.kind: daily digest vs weekly highlights

Revision ID: f6postkind01
Revises: e5posts01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6postkind01"
down_revision: Union[str, None] = "e5posts01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("posts", sa.Column("kind", sa.String(20), nullable=False, server_default="daily"))
    op.create_index("ix_posts_kind", "posts", ["kind"])


def downgrade() -> None:
    op.drop_index("ix_posts_kind", table_name="posts")
    op.drop_column("posts", "kind")
