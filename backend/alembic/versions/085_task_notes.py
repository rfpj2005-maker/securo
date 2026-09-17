"""add notes to tasks

Revision ID: 085
Revises: 084
Create Date: 2026-09-03

Free-text "observações" field for a task — optional context that doesn't
fit in the title (who to contact, a link, extra instructions), shown and
edited alongside the subtasks in the edit dialog.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "085"
down_revision: Union[str, None] = "084"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "notes")
