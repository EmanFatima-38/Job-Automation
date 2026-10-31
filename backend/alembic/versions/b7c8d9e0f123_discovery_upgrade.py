"""Add discovery intelligence without replacing existing records or contracts."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'b7c8d9e0f123'
down_revision = 'a6f3c0d9b218'
branch_labels = None
depends_on = None


def upgrade():
    for table, name in [('users', 'preferences'), ('users', 'portfolio_data'),
                        ('jobs', 'research'), ('matches', 'details'), ('crawl_runs', 'plan')]:
        op.add_column(table, sa.Column(name, postgresql.JSONB(), nullable=False, server_default='{}'))
    op.add_column('jobs', sa.Column('canonical_url', sa.String(2048), nullable=True))
    op.add_column('jobs', sa.Column('fingerprint', sa.String(64), nullable=True))
    op.create_index('ix_jobs_canonical_url', 'jobs', ['canonical_url'])
    op.create_index('ix_jobs_fingerprint', 'jobs', ['fingerprint'])
    op.add_column('matches', sa.Column('context_hash', sa.Text(), nullable=True))
    op.add_column('crawl_runs', sa.Column('intent', sa.Text(), nullable=False, server_default=''))
    op.create_table('opportunity_deliveries',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('job_id', sa.UUID(), sa.ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.UniqueConstraint('user_id', 'job_id', name='uq_opportunity_delivery'))


def downgrade():
    op.drop_table('opportunity_deliveries')
    op.drop_column('crawl_runs', 'intent')
    op.drop_column('matches', 'context_hash')
    op.drop_index('ix_jobs_fingerprint', table_name='jobs')
    op.drop_index('ix_jobs_canonical_url', table_name='jobs')
    op.drop_column('jobs', 'fingerprint')
    op.drop_column('jobs', 'canonical_url')
    for table, name in [('users', 'preferences'), ('users', 'portfolio_data'),
                        ('jobs', 'research'), ('matches', 'details'), ('crawl_runs', 'plan')]:
        op.drop_column(table, name)
