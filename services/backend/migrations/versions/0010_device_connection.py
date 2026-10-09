"""device connection settings and sealed secret (ADR 0016, expand only)

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-09 15:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('devices', schema=None) as batch_op:
        batch_op.add_column(sa.Column('connection', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('secret_enc', sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('devices', schema=None) as batch_op:
        batch_op.drop_column('secret_enc')
        batch_op.drop_column('connection')
