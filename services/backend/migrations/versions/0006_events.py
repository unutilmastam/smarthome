"""events (ADR 0012, expand only)

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-07 18:33:41.550038
"""
from alembic import op
import sqlalchemy as sa
import app.db.types


revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('events',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('home_id', sa.Uuid(), nullable=False),
    sa.Column('device_id', sa.Uuid(), nullable=True),
    sa.Column('device_key', sa.String(length=64), nullable=False),
    sa.Column('type', sa.String(length=64), nullable=False),
    sa.Column('severity', sa.String(length=16), nullable=False),
    sa.Column('ts', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('data', sa.JSON(), nullable=False),
    sa.Column('created_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], name=op.f('fk_events_device_id_devices'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['home_id'], ['homes.id'], name=op.f('fk_events_home_id_homes'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_events'))
    )
    with op.batch_alter_table('events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_events_device_id'), ['device_id'], unique=False)
        batch_op.create_index('ix_events_home_ts', ['home_id', 'ts'], unique=False)



def downgrade() -> None:
    with op.batch_alter_table('events', schema=None) as batch_op:
        batch_op.drop_index('ix_events_home_ts')
        batch_op.drop_index(batch_op.f('ix_events_device_id'))

    op.drop_table('events')
