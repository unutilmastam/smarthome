"""hub health (Faza 14, expand only)

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-08 04:51:42.005200
"""
from alembic import op
import sqlalchemy as sa
import app.db.types


revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('hubs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('health', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('health_alerts', sa.JSON(), nullable=True))



def downgrade() -> None:
    with op.batch_alter_table('hubs', schema=None) as batch_op:
        batch_op.drop_column('health_alerts')
        batch_op.drop_column('health')

