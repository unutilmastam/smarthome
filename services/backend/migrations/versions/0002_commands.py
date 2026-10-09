"""commands

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-07 13:45:21.126800
"""
from alembic import op
import sqlalchemy as sa
import app.db.types


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('commands',
    sa.Column('home_id', sa.Uuid(), nullable=False),
    sa.Column('device_id', sa.Uuid(), nullable=False),
    sa.Column('hub_id', sa.Uuid(), nullable=True),
    sa.Column('capability', sa.String(length=40), nullable=False),
    sa.Column('action', sa.String(length=40), nullable=False),
    sa.Column('params', sa.JSON(), nullable=False),
    sa.Column('risk', sa.String(length=8), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('reason', sa.String(length=32), nullable=True),
    sa.Column('detail', sa.String(length=500), nullable=True),
    sa.Column('requested_by', sa.Uuid(), nullable=False),
    sa.Column('requested_role', sa.String(length=16), nullable=False),
    sa.Column('idempotency_key', sa.String(length=80), nullable=False),
    sa.Column('envelope', sa.JSON(), nullable=False),
    sa.Column('created_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('expires_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('sent_at', app.db.types.UTCDateTime(timezone=True), nullable=True),
    sa.Column('acked_at', app.db.types.UTCDateTime(timezone=True), nullable=True),
    sa.Column('finished_at', app.db.types.UTCDateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.CheckConstraint("status IN ('queued','sent','acked','confirmed','rejected','failed','expired','timeout')", name=op.f('ck_commands_status_valid')),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], name=op.f('fk_commands_device_id_devices'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['home_id'], ['homes.id'], name=op.f('fk_commands_home_id_homes'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['hub_id'], ['hubs.id'], name=op.f('fk_commands_hub_id_hubs'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['requested_by'], ['users.id'], name=op.f('fk_commands_requested_by_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_commands')),
    sa.UniqueConstraint('requested_by', 'idempotency_key', name='uq_commands_user_idem')
    )
    with op.batch_alter_table('commands', schema=None) as batch_op:
        batch_op.create_index('ix_commands_device_created', ['device_id', 'created_at'], unique=False)
        batch_op.create_index('ix_commands_home_status', ['home_id', 'status'], unique=False)

    op.create_table('command_events',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('command_id', sa.Uuid(), nullable=False),
    sa.Column('ts', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('source', sa.String(length=16), nullable=False),
    sa.Column('applied', sa.Boolean(), nullable=False),
    sa.Column('reason', sa.String(length=32), nullable=True),
    sa.Column('detail', sa.String(length=500), nullable=True),
    sa.ForeignKeyConstraint(['command_id'], ['commands.id'], name=op.f('fk_command_events_command_id_commands'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_command_events'))
    )
    with op.batch_alter_table('command_events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_command_events_command_id'), ['command_id'], unique=False)



def downgrade() -> None:
    with op.batch_alter_table('command_events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_command_events_command_id'))

    op.drop_table('command_events')
    with op.batch_alter_table('commands', schema=None) as batch_op:
        batch_op.drop_index('ix_commands_home_status')
        batch_op.drop_index('ix_commands_device_created')

    op.drop_table('commands')
