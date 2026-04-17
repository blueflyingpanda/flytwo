"""add notify_on_decrease to directions

Revision ID: e8f1a2b3c4d5
Revises: fb59b70078aa
Create Date: 2026-04-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e8f1a2b3c4d5'
down_revision: Union[str, None] = 'fb59b70078aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('directions', sa.Column('notify_on_decrease', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('directions', 'notify_on_decrease')