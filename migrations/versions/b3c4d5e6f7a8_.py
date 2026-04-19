"""merge schedule and rrule into schedule string

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-04-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, None] = 'a2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_RRULE = 'FREQ=HOURLY;INTERVAL=1'


def upgrade() -> None:
    op.drop_column('chats', 'rrule')
    op.execute(f"ALTER TABLE chats ALTER COLUMN schedule TYPE VARCHAR USING '{DEFAULT_RRULE}', ALTER COLUMN schedule SET DEFAULT '{DEFAULT_RRULE}'")


def downgrade() -> None:
    op.execute("ALTER TABLE chats ALTER COLUMN schedule TYPE BOOLEAN USING (schedule != ''), ALTER COLUMN schedule SET DEFAULT FALSE")
    op.add_column('chats', sa.Column('rrule', sa.String(), server_default=f"'{DEFAULT_RRULE}'", nullable=False))