"""cameras link and hub hosts

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-07 15:25:35.368156
"""
from alembic import op
import sqlalchemy as sa
import app.db.types


revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('cameras', schema=None) as batch_op:
        batch_op.add_column(sa.Column('device_id', sa.Uuid(), nullable=True))
        batch_op.create_unique_constraint(batch_op.f('uq_cameras_device_id'), ['device_id'])
        batch_op.create_unique_constraint('uq_cameras_home_frigate', ['home_id', 'frigate_name'])
        batch_op.create_foreign_key(batch_op.f('fk_cameras_device_id_devices'), 'devices', ['device_id'], ['id'], ondelete='CASCADE')

    with op.batch_alter_table('hubs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tailnet_host', sa.String(length=253), nullable=True))
        batch_op.add_column(sa.Column('lan_host', sa.String(length=253), nullable=True))



def downgrade() -> None:
    with op.batch_alter_table('hubs', schema=None) as batch_op:
        batch_op.drop_column('lan_host')
        batch_op.drop_column('tailnet_host')

    with op.batch_alter_table('cameras', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_cameras_device_id_devices'), type_='foreignkey')
        batch_op.drop_constraint('uq_cameras_home_frigate', type_='unique')
        batch_op.drop_constraint(batch_op.f('uq_cameras_device_id'), type_='unique')
        batch_op.drop_column('device_id')

