"""add email_accounts and followups

Revision ID: a6f3c0d9b218
Revises: 5b4ad7417451
Create Date: 2026-10-03 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a6f3c0d9b218'
down_revision: Union[str, None] = '5b4ad7417451'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('email_accounts',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('smtp_host', sa.String(length=255), nullable=False),
    sa.Column('smtp_port', sa.Integer(), server_default=sa.text('587'), nullable=False),
    sa.Column('smtp_username', sa.String(length=255), nullable=False),
    sa.Column('encrypted_password', sa.Text(), nullable=False),
    sa.Column('from_name', sa.String(length=255), nullable=True),
    sa.Column('from_email', sa.String(length=255), nullable=False),
    sa.Column('use_tls', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('last_tested_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_test_ok', sa.Boolean(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', name='uq_email_account_user')
    )
    op.create_index(op.f('ix_email_accounts_user_id'), 'email_accounts', ['user_id'], unique=True)

    op.create_table('followups',
    sa.Column('application_id', sa.UUID(), nullable=False),
    sa.Column('sent_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('subject', sa.Text(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_followups_application_id'), 'followups', ['application_id'], unique=False)

    op.add_column(
        'users',
        sa.Column('followup_enabled', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    )
    op.add_column(
        'users',
        sa.Column('followup_first_days', sa.Integer(), server_default=sa.text('4'), nullable=False),
    )
    op.add_column(
        'users',
        sa.Column('followup_interval_days', sa.Integer(), server_default=sa.text('5'), nullable=False),
    )
    op.add_column(
        'users',
        sa.Column('followup_max_count', sa.Integer(), server_default=sa.text('2'), nullable=False),
    )
    op.add_column(
        'applications',
        sa.Column('followup_opt_out', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    )


def downgrade() -> None:
    op.drop_column('applications', 'followup_opt_out')
    op.drop_column('users', 'followup_max_count')
    op.drop_column('users', 'followup_interval_days')
    op.drop_column('users', 'followup_first_days')
    op.drop_column('users', 'followup_enabled')
    op.drop_index(op.f('ix_followups_application_id'), table_name='followups')
    op.drop_table('followups')
    op.drop_index(op.f('ix_email_accounts_user_id'), table_name='email_accounts')
    op.drop_table('email_accounts')
