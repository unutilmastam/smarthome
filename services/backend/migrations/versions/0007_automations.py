"""automations (ADR 0013, expand only)

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-07 19:42:39.607401
"""
from alembic import op
import sqlalchemy as sa
import app.db.types


revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('automations',
    sa.Column('home_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('definition', sa.JSON(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('updated_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_automations_created_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['home_id'], ['homes.id'], name=op.f('fk_automations_home_id_homes'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_automations'))
    )
    with op.batch_alter_table('automations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_automations_home_id'), ['home_id'], unique=False)

    op.create_table('automation_runs',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('home_id', sa.Uuid(), nullable=False),
    sa.Column('automation_id', sa.Uuid(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('ts', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.Column('trigger', sa.String(length=160), nullable=False),
    sa.Column('result', sa.String(length=16), nullable=False),
    sa.Column('reason', sa.String(length=64), nullable=True),
    sa.Column('actions', sa.JSON(), nullable=False),
    sa.Column('created_at', app.db.types.UTCDateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['automation_id'], ['automations.id'], name=op.f('fk_automation_runs_automation_id_automations'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['home_id'], ['homes.id'], name=op.f('fk_automation_runs_home_id_homes'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_automation_runs'))
    )
    with op.batch_alter_table('automation_runs', schema=None) as batch_op:
        batch_op.create_index('ix_automation_runs_automation_ts', ['automation_id', 'ts'], unique=False)
        batch_op.create_index(batch_op.f('ix_automation_runs_home_id'), ['home_id'], unique=False)



def downgrade() -> None:
    with op.batch_alter_table('automation_runs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_automation_runs_home_id'))
        batch_op.drop_index('ix_automation_runs_automation_ts')

    op.drop_table('automation_runs')
    with op.batch_alter_table('automations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_automations_home_id'))

    op.drop_table('automations')
