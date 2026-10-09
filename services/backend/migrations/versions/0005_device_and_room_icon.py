"""device and room icon (expand only)

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-07 18:30:00
"""
from alembic import op
import sqlalchemy as sa


revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('devices', schema=None) as batch_op:
        batch_op.add_column(sa.Column('icon', sa.String(length=32), nullable=True))
    with op.batch_alter_table('rooms', schema=None) as batch_op:
        batch_op.add_column(sa.Column('icon', sa.String(length=32), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('rooms', schema=None) as batch_op:
        batch_op.drop_column('icon')
    with op.batch_alter_table('devices', schema=None) as batch_op:
        batch_op.drop_column('icon')
