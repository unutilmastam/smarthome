"""notifications (ADR 0014, expand only)

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-08 01:24:56.914818
"""
from alembic import op
import sqlalchemy as sa
import app.db.types


revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('notifications',
    sa.Column('home_id', sa.Uuid(), nullable=False),
    sa.Column('severity', sa.String(length=16), nullable=False),
    sa.Column('source', sa.String(length=16), nullable=False),
    sa.Column('kind', sa.String(length=64), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('body', sa.String(length=1000), nullable=False),
    sa.Column('data', sa.JSON(), nullable=False),
    sa.Column('ts', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('dedupe_key', sa.String(length=120), nullable=True),
    sa.Column('created_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('acked_by', sa.Uuid(), nullable=True),
    sa.Column('acked_at', app.db.types.UTCDateTime(timezone=True), nullable=True),
    sa.Column('reminded_at', app.db.types.UTCDateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['acked_by'], ['users.id'], name=op.f('fk_notifications_acked_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['home_id'], ['homes.id'], name=op.f('fk_notifications_home_id_homes'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notifications'))
    )
    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.create_index('ix_notifications_home_created', ['home_id', 'created_at'], unique=False)
        batch_op.create_index('uq_notifications_home_dedupe', ['home_id', 'dedupe_key'], unique=True)

    op.create_table('push_subscriptions',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('endpoint', sa.String(length=1024), nullable=False),
    sa.Column('p256dh', sa.String(length=128), nullable=False),
    sa.Column('auth', sa.String(length=64), nullable=False),
    sa.Column('user_agent', sa.String(length=200), nullable=True),
    sa.Column('created_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('last_success_at', app.db.types.UTCDateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_push_subscriptions_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_push_subscriptions')),
    sa.UniqueConstraint('endpoint', name=op.f('uq_push_subscriptions_endpoint'))
    )
    with op.batch_alter_table('push_subscriptions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_push_subscriptions_user_id'), ['user_id'], unique=False)

    op.create_table('telegram_link_codes',
    sa.Column('code_hash', sa.String(length=64), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('expires_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('used_at', app.db.types.UTCDateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_telegram_link_codes_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('code_hash', name=op.f('pk_telegram_link_codes'))
    )
    with op.batch_alter_table('telegram_link_codes', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_telegram_link_codes_user_id'), ['user_id'], unique=False)

    op.create_table('telegram_links',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('chat_id', sa.String(length=32), nullable=False),
    sa.Column('username', sa.String(length=64), nullable=True),
    sa.Column('created_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_telegram_links_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_telegram_links')),
    sa.UniqueConstraint('chat_id', name=op.f('uq_telegram_links_chat_id'))
    )
    with op.batch_alter_table('telegram_links', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_telegram_links_user_id'), ['user_id'], unique=False)

    op.create_table('notification_deliveries',
    sa.Column('notification_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('channel', sa.String(length=16), nullable=False),
    sa.Column('target', sa.String(length=64), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('next_attempt_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('claimed_at', app.db.types.UTCDateTime(timezone=True), nullable=True),
    sa.Column('sent_at', app.db.types.UTCDateTime(timezone=True), nullable=True),
    sa.Column('error', sa.String(length=200), nullable=True),
    sa.Column('reminder', sa.Integer(), nullable=False),
    sa.Column('created_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['notification_id'], ['notifications.id'], name=op.f('fk_notification_deliveries_notification_id_notifications'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_notification_deliveries_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notification_deliveries'))
    )
    with op.batch_alter_table('notification_deliveries', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_notification_deliveries_notification_id'), ['notification_id'], unique=False)
        batch_op.create_index('ix_notification_deliveries_status_next', ['status', 'next_attempt_at'], unique=False)

    with op.batch_alter_table('devices', schema=None) as batch_op:
        batch_op.add_column(sa.Column('offline_notified_at', app.db.types.UTCDateTime(timezone=True), nullable=True))

    with op.batch_alter_table('home_members', schema=None) as batch_op:
        batch_op.add_column(sa.Column('notify_min_severity', sa.String(length=16), server_default='warning', nullable=False))

    with op.batch_alter_table('hubs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('offline_notified_at', app.db.types.UTCDateTime(timezone=True), nullable=True))



def downgrade() -> None:
    with op.batch_alter_table('hubs', schema=None) as batch_op:
        batch_op.drop_column('offline_notified_at')

    with op.batch_alter_table('home_members', schema=None) as batch_op:
        batch_op.drop_column('notify_min_severity')

    with op.batch_alter_table('devices', schema=None) as batch_op:
        batch_op.drop_column('offline_notified_at')

    with op.batch_alter_table('notification_deliveries', schema=None) as batch_op:
        batch_op.drop_index('ix_notification_deliveries_status_next')
        batch_op.drop_index(batch_op.f('ix_notification_deliveries_notification_id'))

    op.drop_table('notification_deliveries')
    with op.batch_alter_table('telegram_links', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_telegram_links_user_id'))

    op.drop_table('telegram_links')
    with op.batch_alter_table('telegram_link_codes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_telegram_link_codes_user_id'))

    op.drop_table('telegram_link_codes')
    with op.batch_alter_table('push_subscriptions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_push_subscriptions_user_id'))

    op.drop_table('push_subscriptions')
    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.drop_index('uq_notifications_home_dedupe')
        batch_op.drop_index('ix_notifications_home_created')

    op.drop_table('notifications')
