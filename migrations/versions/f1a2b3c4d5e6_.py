"""add threshold to directions

Revision ID: f1a2b3c4d5e6
Revises: e8f1a2b3c4d5
Create Date: 2026-04-17 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e8f1a2b3c4d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('directions', sa.Column('threshold', sa.Integer(), server_default='0', nullable=False))


def downgrade() -> None:
    op.drop_column('directions', 'threshold')