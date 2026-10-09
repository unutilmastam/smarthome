"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-10-07 13:38:41.810890
"""
from alembic import op
import sqlalchemy as sa
import app.db.types


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('homes',
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('timezone', sa.String(length=64), nullable=False),
    sa.Column('latitude', sa.Float(), nullable=True),
    sa.Column('longitude', sa.Float(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('updated_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_homes'))
    )
    op.create_table('rate_limits',
    sa.Column('key', sa.String(length=200), nullable=False),
    sa.Column('window_start', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('count', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('key', 'window_start', name=op.f('pk_rate_limits'))
    )
    with op.batch_alter_table('rate_limits', schema=None) as batch_op:
        batch_op.create_index('ix_rate_limits_window_start', ['window_start'], unique=False)

    op.create_table('users',
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('pin_hash', sa.String(length=255), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('failed_logins', sa.Integer(), nullable=False),
    sa.Column('locked_until', app.db.types.UTCDateTime(timezone=True), nullable=True),
    sa.Column('password_changed_at', app.db.types.UTCDateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('updated_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('email', name=op.f('uq_users_email'))
    )
    op.create_table('audit_log',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('ts', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('home_id', sa.Uuid(), nullable=True),
    sa.Column('actor_type', sa.String(length=16), nullable=False),
    sa.Column('actor_id', sa.Uuid(), nullable=True),
    sa.Column('action', sa.String(length=64), nullable=False),
    sa.Column('target_type', sa.String(length=32), nullable=True),
    sa.Column('target_id', sa.String(length=64), nullable=True),
    sa.Column('ip', sa.String(length=64), nullable=True),
    sa.Column('details', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['home_id'], ['homes.id'], name=op.f('fk_audit_log_home_id_homes'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_log'))
    )
    with op.batch_alter_table('audit_log', schema=None) as batch_op:
        batch_op.create_index('ix_audit_log_actor_ts', ['actor_id', 'ts'], unique=False)
        batch_op.create_index('ix_audit_log_home_ts', ['home_id', 'ts'], unique=False)

    op.create_table('auth_sessions',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('refresh_hash', sa.String(length=64), nullable=False),
    sa.Column('created_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('last_used_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('expires_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', app.db.types.UTCDateTime(timezone=True), nullable=True),
    sa.Column('revoke_reason', sa.String(length=40), nullable=True),
    sa.Column('ip', sa.String(length=64), nullable=True),
    sa.Column('user_agent', sa.String(length=255), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_auth_sessions_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_auth_sessions'))
    )
    with op.batch_alter_table('auth_sessions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_auth_sessions_user_id'), ['user_id'], unique=False)

    op.create_table('floors',
    sa.Column('home_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('level', sa.Integer(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('updated_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['home_id'], ['homes.id'], name=op.f('fk_floors_home_id_homes'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_floors'))
    )
    with op.batch_alter_table('floors', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_floors_home_id'), ['home_id'], unique=False)

    op.create_table('home_members',
    sa.Column('home_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('role', sa.String(length=16), nullable=False),
    sa.Column('created_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('updated_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.CheckConstraint("role IN ('owner','admin','family','guest','viewer')", name=op.f('ck_home_members_role_valid')),
    sa.ForeignKeyConstraint(['home_id'], ['homes.id'], name=op.f('fk_home_members_home_id_homes'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_home_members_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('home_id', 'user_id', name=op.f('pk_home_members'))
    )
    with op.batch_alter_table('home_members', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_home_members_user_id'), ['user_id'], unique=False)
        batch_op.create_index('uq_home_members_one_owner', ['home_id'], unique=True, postgresql_where=sa.text("role = 'owner'"), sqlite_where=sa.text("role = 'owner'"))

    op.create_table('hubs',
    sa.Column('home_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('last_seen', app.db.types.UTCDateTime(timezone=True), nullable=True),
    sa.Column('version', sa.String(length=40), nullable=True),
    sa.Column('revoked_at', app.db.types.UTCDateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('updated_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.CheckConstraint("status IN ('active','revoked')", name=op.f('ck_hubs_status_valid')),
    sa.ForeignKeyConstraint(['home_id'], ['homes.id'], name=op.f('fk_hubs_home_id_homes'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_hubs')),
    sa.UniqueConstraint('token_hash', name=op.f('uq_hubs_token_hash'))
    )
    with op.batch_alter_table('hubs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_hubs_home_id'), ['home_id'], unique=False)
        batch_op.create_index('uq_hubs_one_active_per_home', ['home_id'], unique=True, postgresql_where=sa.text("status = 'active'"), sqlite_where=sa.text("status = 'active'"))

    op.create_table('rooms',
    sa.Column('home_id', sa.Uuid(), nullable=False),
    sa.Column('floor_id', sa.Uuid(), nullable=True),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('type', sa.String(length=16), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('updated_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.CheckConstraint("type IN ('indoor','outdoor')", name=op.f('ck_rooms_type_valid')),
    sa.ForeignKeyConstraint(['floor_id'], ['floors.id'], name=op.f('fk_rooms_floor_id_floors'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['home_id'], ['homes.id'], name=op.f('fk_rooms_home_id_homes'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_rooms'))
    )
    with op.batch_alter_table('rooms', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_rooms_home_id'), ['home_id'], unique=False)

    op.create_table('cameras',
    sa.Column('home_id', sa.Uuid(), nullable=False),
    sa.Column('hub_id', sa.Uuid(), nullable=True),
    sa.Column('room_id', sa.Uuid(), nullable=True),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('frigate_name', sa.String(length=64), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('updated_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['home_id'], ['homes.id'], name=op.f('fk_cameras_home_id_homes'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['hub_id'], ['hubs.id'], name=op.f('fk_cameras_hub_id_hubs'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], name=op.f('fk_cameras_room_id_rooms'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_cameras'))
    )
    with op.batch_alter_table('cameras', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_cameras_home_id'), ['home_id'], unique=False)

    op.create_table('devices',
    sa.Column('home_id', sa.Uuid(), nullable=False),
    sa.Column('room_id', sa.Uuid(), nullable=True),
    sa.Column('key', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('adapter', sa.String(length=40), nullable=False),
    sa.Column('protocol', sa.String(length=40), nullable=False),
    sa.Column('model', sa.String(length=120), nullable=True),
    sa.Column('fail_safe_state', sa.JSON(), nullable=True),
    sa.Column('unsupported', sa.JSON(), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('availability', sa.String(length=16), nullable=False),
    sa.Column('availability_ts', app.db.types.UTCDateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('updated_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.CheckConstraint("availability IN ('online','offline','unknown')", name=op.f('ck_devices_availability_valid')),
    sa.ForeignKeyConstraint(['home_id'], ['homes.id'], name=op.f('fk_devices_home_id_homes'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], name=op.f('fk_devices_room_id_rooms'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_devices')),
    sa.UniqueConstraint('home_id', 'key', name='uq_devices_home_key')
    )
    with op.batch_alter_table('devices', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_devices_home_id'), ['home_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_devices_room_id'), ['room_id'], unique=False)

    op.create_table('device_capabilities',
    sa.Column('device_id', sa.Uuid(), nullable=False),
    sa.Column('capability', sa.String(length=40), nullable=False),
    sa.Column('config_json', sa.JSON(), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], name=op.f('fk_device_capabilities_device_id_devices'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('device_id', 'capability', name=op.f('pk_device_capabilities'))
    )
    op.create_table('device_state',
    sa.Column('device_id', sa.Uuid(), nullable=False),
    sa.Column('capability', sa.String(length=40), nullable=False),
    sa.Column('attribute', sa.String(length=40), nullable=False),
    sa.Column('value_json', sa.JSON(), nullable=False),
    sa.Column('source', sa.String(length=16), nullable=False),
    sa.Column('quality', sa.String(length=16), nullable=False),
    sa.Column('ts', app.db.types.UTCDateTime(timezone=True), nullable=True),
    sa.Column('updated_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.CheckConstraint("quality IN ('good','stale','unknown','not_supported')", name=op.f('ck_device_state_quality_valid')),
    sa.CheckConstraint("source IN ('reported','assumed','computed')", name=op.f('ck_device_state_source_valid')),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], name=op.f('fk_device_state_device_id_devices'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('device_id', 'capability', 'attribute', name=op.f('pk_device_state'))
    )


def downgrade() -> None:
    op.drop_table('device_state')
    op.drop_table('device_capabilities')
    with op.batch_alter_table('devices', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_devices_room_id'))
        batch_op.drop_index(batch_op.f('ix_devices_home_id'))

    op.drop_table('devices')
    with op.batch_alter_table('cameras', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_cameras_home_id'))

    op.drop_table('cameras')
    with op.batch_alter_table('rooms', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_rooms_home_id'))

    op.drop_table('rooms')
    with op.batch_alter_table('hubs', schema=None) as batch_op:
        batch_op.drop_index('uq_hubs_one_active_per_home', postgresql_where=sa.text("status = 'active'"), sqlite_where=sa.text("status = 'active'"))
        batch_op.drop_index(batch_op.f('ix_hubs_home_id'))

    op.drop_table('hubs')
    with op.batch_alter_table('home_members', schema=None) as batch_op:
        batch_op.drop_index('uq_home_members_one_owner', postgresql_where=sa.text("role = 'owner'"), sqlite_where=sa.text("role = 'owner'"))
        batch_op.drop_index(batch_op.f('ix_home_members_user_id'))

    op.drop_table('home_members')
    with op.batch_alter_table('floors', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_floors_home_id'))

    op.drop_table('floors')
    with op.batch_alter_table('auth_sessions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_auth_sessions_user_id'))

    op.drop_table('auth_sessions')
    with op.batch_alter_table('audit_log', schema=None) as batch_op:
        batch_op.drop_index('ix_audit_log_home_ts')
        batch_op.drop_index('ix_audit_log_actor_ts')

    op.drop_table('audit_log')
    op.drop_table('users')
    with op.batch_alter_table('rate_limits', schema=None) as batch_op:
        batch_op.drop_index('ix_rate_limits_window_start')

    op.drop_table('rate_limits')
    op.drop_table('homes')
