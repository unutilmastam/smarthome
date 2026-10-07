"""telemetry and tariff

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-07 15:16:11.204252
"""
from alembic import op
import sqlalchemy as sa
import app.db.types


revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('energy_daily',
    sa.Column('device_id', sa.Uuid(), nullable=False),
    sa.Column('day', sa.Date(), nullable=False),
    sa.Column('kwh', sa.Float(), nullable=False),
    sa.Column('cost', sa.Float(), nullable=True),
    sa.Column('currency', sa.String(length=3), nullable=True),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], name=op.f('fk_energy_daily_device_id_devices'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('device_id', 'day', name=op.f('pk_energy_daily'))
    )
    op.create_table('telemetry_1h',
    sa.Column('device_id', sa.Uuid(), nullable=False),
    sa.Column('metric', sa.String(length=64), nullable=False),
    sa.Column('ts', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('avg', sa.Float(), nullable=False),
    sa.Column('min', sa.Float(), nullable=False),
    sa.Column('max', sa.Float(), nullable=False),
    sa.Column('last', sa.Float(), nullable=False),
    sa.Column('count', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], name=op.f('fk_telemetry_1h_device_id_devices'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('device_id', 'metric', 'ts', name=op.f('pk_telemetry_1h'))
    )
    op.create_table('telemetry_1m',
    sa.Column('device_id', sa.Uuid(), nullable=False),
    sa.Column('metric', sa.String(length=64), nullable=False),
    sa.Column('ts', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('avg', sa.Float(), nullable=False),
    sa.Column('min', sa.Float(), nullable=False),
    sa.Column('max', sa.Float(), nullable=False),
    sa.Column('last', sa.Float(), nullable=False),
    sa.Column('count', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], name=op.f('fk_telemetry_1m_device_id_devices'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('device_id', 'metric', 'ts', name=op.f('pk_telemetry_1m'))
    )
    with op.batch_alter_table('homes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tariff_per_kwh', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('currency', sa.String(length=3), server_default='UZS', nullable=False))



def downgrade() -> None:
    with op.batch_alter_table('homes', schema=None) as batch_op:
        batch_op.drop_column('currency')
        batch_op.drop_column('tariff_per_kwh')

    op.drop_table('telemetry_1m')
    op.drop_table('telemetry_1h')
    op.drop_table('energy_daily')
