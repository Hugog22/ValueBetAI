"""Add free tier usage tracking fields to users

Revision ID: a1b2c3d4e5f6
Revises: df57f4d6adb8
Create Date: 2026-09-03 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'df57f4d6adb8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column(
            'free_analyses_used',
            sa.Integer(),
            nullable=False,
            server_default='0',
        )
    )
    op.add_column(
        'users',
        sa.Column(
            'free_analyses_reset_at',
            sa.DateTime(),
            nullable=True,
        )
    )


def downgrade() -> None:
    op.drop_column('users', 'free_analyses_reset_at')
    op.drop_column('users', 'free_analyses_used')
