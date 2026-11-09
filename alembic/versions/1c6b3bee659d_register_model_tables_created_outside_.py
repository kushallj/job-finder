"""register model tables created outside migrations

Answer Bank, NextRaise, Tsenta and Workday tables were declared on Base but no migration
created them: local databases had them only via create_all, and a fresh
`alembic upgrade head` (production) did not. Each table is created only if missing, so
existing databases are untouched. Model modules now load via src/model_registry.py.

Revision ID: 1c6b3bee659d
Revises: 9a3e51c0d7b2
Create Date: 2026-11-09 11:04:00.725131

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1c6b3bee659d'
down_revision: Union[str, None] = '9a3e51c0d7b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _missing(inspector: sa.Inspector, table: str) -> bool:
    return not inspector.has_table(table)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if _missing(inspector, 'answered_questions'):
        op.create_table('answered_questions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('normalized_question', sa.String(length=500), nullable=False),
        sa.Column('answer_text', sa.Text(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('context', sa.String(length=50), nullable=True),
        sa.Column('approved', sa.Boolean(), nullable=True),
        sa.Column('times_used', sa.Integer(), nullable=True),
        sa.Column('match_confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_answered_questions_normalized_question'), 'answered_questions', ['normalized_question'], unique=False)
    if _missing(inspector, 'nextraise_config'):
        op.create_table('nextraise_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_email', sa.String(length=255), nullable=False),
        sa.Column('oauth_access_token', sa.Text(), nullable=True),
        sa.Column('oauth_refresh_token', sa.Text(), nullable=True),
        sa.Column('session_token', sa.Text(), nullable=True),
        sa.Column('oauth_connected', sa.Boolean(), nullable=True),
        sa.Column('mode', sa.String(length=50), nullable=True),
        sa.Column('daily_target', sa.Integer(), nullable=True),
        sa.Column('min_fit_score', sa.Float(), nullable=True),
        sa.Column('auto_batch_enabled', sa.Boolean(), nullable=True),
        sa.Column('batch_concurrency', sa.Integer(), nullable=True),
        sa.Column('enabled_ats_json', sa.Text(), nullable=True),
        sa.Column('api_url', sa.String(length=255), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
    if _missing(inspector, 'nextraise_quota'):
        op.create_table('nextraise_quota',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('daily_used', sa.Integer(), nullable=True),
        sa.Column('daily_limit', sa.Integer(), nullable=True),
        sa.Column('total_submitted', sa.Integer(), nullable=True),
        sa.Column('total_failed', sa.Integer(), nullable=True),
        sa.Column('active_tier', sa.String(length=50), nullable=True),
        sa.Column('last_reset_date', sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
    if _missing(inspector, 'tsenta_configs'):
        op.create_table('tsenta_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('api_key', sa.String(length=255), nullable=True),
        sa.Column('api_url', sa.String(length=255), nullable=True),
        sa.Column('mode', sa.String(length=50), nullable=True),
        sa.Column('min_fit_score', sa.Integer(), nullable=True),
        sa.Column('auto_apply_enabled', sa.Boolean(), nullable=True),
        sa.Column('notification_webhook', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_tsenta_configs_id'), 'tsenta_configs', ['id'], unique=False)
    if _missing(inspector, 'tsenta_quotas'):
        op.create_table('tsenta_quotas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('daily_used', sa.Integer(), nullable=True),
        sa.Column('daily_limit', sa.Integer(), nullable=True),
        sa.Column('total_submitted', sa.Integer(), nullable=True),
        sa.Column('lifetime_free_remaining', sa.Integer(), nullable=True),
        sa.Column('active_tier', sa.String(length=50), nullable=True),
        sa.Column('last_reset_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_tsenta_quotas_id'), 'tsenta_quotas', ['id'], unique=False)
    if _missing(inspector, 'workday_accounts'):
        op.create_table('workday_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_domain', sa.String(length=255), nullable=False),
        sa.Column('career_site_name', sa.String(length=100), nullable=False),
        sa.Column('company_name', sa.String(length=255), nullable=False),
        sa.Column('account_email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('session_cookies_json', sa.Text(), nullable=True),
        sa.Column('auth_token', sa.Text(), nullable=True),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_workday_accounts_id'), 'workday_accounts', ['id'], unique=False)
        op.create_index(op.f('ix_workday_accounts_tenant_domain'), 'workday_accounts', ['tenant_domain'], unique=False)
    if _missing(inspector, 'workday_candidate_profiles'):
        op.create_table('workday_candidate_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_email', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('middle_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('preferred_name', sa.String(length=100), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('phone_device_type', sa.String(length=50), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('address_line1', sa.String(length=255), nullable=True),
        sa.Column('address_line2', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state_province', sa.String(length=100), nullable=True),
        sa.Column('postal_code', sa.String(length=50), nullable=True),
        sa.Column('linkedin_url', sa.String(length=255), nullable=True),
        sa.Column('github_url', sa.String(length=255), nullable=True),
        sa.Column('portfolio_url', sa.String(length=255), nullable=True),
        sa.Column('twitter_url', sa.String(length=255), nullable=True),
        sa.Column('headline', sa.String(length=255), nullable=True),
        sa.Column('years_of_experience', sa.Float(), nullable=True),
        sa.Column('current_company', sa.String(length=100), nullable=True),
        sa.Column('current_title', sa.String(length=100), nullable=True),
        sa.Column('skills_json', sa.Text(), nullable=True),
        sa.Column('work_history_json', sa.Text(), nullable=True),
        sa.Column('education_json', sa.Text(), nullable=True),
        sa.Column('legally_authorized', sa.Boolean(), nullable=True),
        sa.Column('requires_sponsorship', sa.Boolean(), nullable=True),
        sa.Column('notice_period_days', sa.Integer(), nullable=True),
        sa.Column('target_salary_min', sa.Float(), nullable=True),
        sa.Column('target_salary_max', sa.Float(), nullable=True),
        sa.Column('salary_currency', sa.String(length=10), nullable=True),
        sa.Column('willing_to_relocate', sa.Boolean(), nullable=True),
        sa.Column('gender', sa.String(length=50), nullable=True),
        sa.Column('hispanic_latino', sa.String(length=50), nullable=True),
        sa.Column('race_ethnicity', sa.String(length=100), nullable=True),
        sa.Column('veteran_status', sa.String(length=100), nullable=True),
        sa.Column('disability_status', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('account_email')
        )
        op.create_index(op.f('ix_workday_candidate_profiles_id'), 'workday_candidate_profiles', ['id'], unique=False)
    if _missing(inspector, 'workday_configs'):
        op.create_table('workday_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_email', sa.String(length=255), nullable=True),
        sa.Column('auto_apply_enabled', sa.Boolean(), nullable=True),
        sa.Column('mode', sa.String(length=50), nullable=True),
        sa.Column('min_fit_score', sa.Float(), nullable=True),
        sa.Column('daily_limit', sa.Integer(), nullable=True),
        sa.Column('daily_used', sa.Integer(), nullable=True),
        sa.Column('total_submitted', sa.Integer(), nullable=True),
        sa.Column('total_failed', sa.Integer(), nullable=True),
        sa.Column('tailor_resumes', sa.Boolean(), nullable=True),
        sa.Column('generate_cover_letters', sa.Boolean(), nullable=True),
        sa.Column('batch_concurrency', sa.Integer(), nullable=True),
        sa.Column('last_reset_date', sa.Date(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_workday_configs_id'), 'workday_configs', ['id'], unique=False)
    if _missing(inspector, 'nextraise_submissions'):
        op.create_table('nextraise_submissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('ats_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('receipt_id', sa.String(length=100), nullable=True),
        sa.Column('proof_url', sa.Text(), nullable=True),
        sa.Column('submission_packet', sa.Text(), nullable=True),
        sa.Column('answers_json', sa.Text(), nullable=True),
        sa.Column('tailored_resume_path', sa.Text(), nullable=True),
        sa.Column('cover_letter_path', sa.Text(), nullable=True),
        sa.Column('tailored_resume_text', sa.Text(), nullable=True),
        sa.Column('cover_letter_text', sa.Text(), nullable=True),
        sa.Column('account_email', sa.String(length=255), nullable=True),
        sa.Column('company_name', sa.String(length=255), nullable=True),
        sa.Column('job_title', sa.String(length=255), nullable=True),
        sa.Column('match_score', sa.Float(), nullable=True),
        sa.Column('error_detail', sa.Text(), nullable=True),
        sa.Column('execution_time_ms', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_nextraise_submissions_account_email'), 'nextraise_submissions', ['account_email'], unique=False)
        op.create_index(op.f('ix_nextraise_submissions_id'), 'nextraise_submissions', ['id'], unique=False)
        op.create_index(op.f('ix_nextraise_submissions_job_id'), 'nextraise_submissions', ['job_id'], unique=False)
        op.create_index(op.f('ix_nextraise_submissions_receipt_id'), 'nextraise_submissions', ['receipt_id'], unique=True)
    if _missing(inspector, 'tsenta_submissions'):
        op.create_table('tsenta_submissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('ats_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('receipt_id', sa.String(length=100), nullable=True),
        sa.Column('proof_url', sa.Text(), nullable=True),
        sa.Column('submission_packet', sa.Text(), nullable=True),
        sa.Column('answers_json', sa.Text(), nullable=True),
        sa.Column('tailored_resume_path', sa.Text(), nullable=True),
        sa.Column('cover_letter_path', sa.Text(), nullable=True),
        sa.Column('tailored_resume_text', sa.Text(), nullable=True),
        sa.Column('cover_letter_text', sa.Text(), nullable=True),
        sa.Column('match_score', sa.Float(), nullable=True),
        sa.Column('company_name', sa.String(length=255), nullable=True),
        sa.Column('job_title', sa.String(length=255), nullable=True),
        sa.Column('error_detail', sa.Text(), nullable=True),
        sa.Column('execution_time_ms', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_tsenta_submissions_id'), 'tsenta_submissions', ['id'], unique=False)
        op.create_index(op.f('ix_tsenta_submissions_job_id'), 'tsenta_submissions', ['job_id'], unique=False)
        op.create_index(op.f('ix_tsenta_submissions_receipt_id'), 'tsenta_submissions', ['receipt_id'], unique=True)
    if _missing(inspector, 'workday_submissions'):
        op.create_table('workday_submissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('tenant_domain', sa.String(length=255), nullable=False),
        sa.Column('company_name', sa.String(length=255), nullable=True),
        sa.Column('job_title', sa.String(length=255), nullable=True),
        sa.Column('account_email', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('receipt_id', sa.String(length=100), nullable=True),
        sa.Column('proof_url', sa.Text(), nullable=True),
        sa.Column('confirmation_number', sa.String(length=100), nullable=True),
        sa.Column('tailored_resume_path', sa.Text(), nullable=True),
        sa.Column('tailored_resume_text', sa.Text(), nullable=True),
        sa.Column('cover_letter_text', sa.Text(), nullable=True),
        sa.Column('match_score', sa.Float(), nullable=True),
        sa.Column('submission_packet_json', sa.Text(), nullable=True),
        sa.Column('answers_json', sa.Text(), nullable=True),
        sa.Column('error_detail', sa.Text(), nullable=True),
        sa.Column('execution_time_ms', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_workday_submissions_id'), 'workday_submissions', ['id'], unique=False)
        op.create_index(op.f('ix_workday_submissions_job_id'), 'workday_submissions', ['job_id'], unique=False)
        op.create_index(op.f('ix_workday_submissions_receipt_id'), 'workday_submissions', ['receipt_id'], unique=True)


def downgrade() -> None:
    # Deliberately a no-op. On databases first built with create_all these tables existed
    # before this revision and may hold data; dropping them on downgrade would destroy it.
    pass
