"""add rrule and last_notified to chats

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-04-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_RRULE = 'FREQ=HOURLY;INTERVAL=1'


def upgrade() -> None:
    op.add_column('chats', sa.Column('rrule', sa.String(), server_default=DEFAULT_RRULE, nullable=False))
    op.add_column('chats', sa.Column('last_notified', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('chats', 'last_notified')
    op.drop_column('chats', 'rrule')