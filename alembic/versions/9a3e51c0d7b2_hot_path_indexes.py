"""hot-path indexes for Jobify list/inbox/chat queries

Revision ID: 9a3e51c0d7b2
Revises: 124e1ce369ff
Create Date: 2026-11-08 12:00:00

Each index backs one hot query (see src/models.py comments):
  jobs(fetched_at) WHERE expired_at IS NULL   GET /api/jobs newest-active scan
  jobs(lower(company))                        founders "hiring" lookup
  applications(user_id, created_at)           GET /api/applications
  chat_conversations(user_id, updated_at)     GET /api/conversations
  inbound_recruiter_messages(mailbox_id, message_id)   dedupe on every ingest
  inbound_recruiter_messages(mailbox_id, received_at)  GET /api/inbox/messages

On a large production Postgres, run these with CREATE INDEX CONCURRENTLY outside a
transaction instead (Alembic: op.get_context().autocommit_block()).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "9a3e51c0d7b2"
down_revision: Union[str, None] = "124e1ce369ff"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ACTIVE = sa.text("expired_at IS NULL")


def upgrade() -> None:
    op.create_index("ix_jobs_active_fetched_at", "jobs", ["fetched_at"],
                    postgresql_where=ACTIVE, sqlite_where=ACTIVE)
    op.create_index("ix_jobs_company_lower", "jobs", [sa.text("lower(company)")])
    op.create_index("ix_applications_user_created", "applications", ["user_id", "created_at"])
    op.create_index("ix_chat_conversations_user_updated", "chat_conversations", ["user_id", "updated_at"])
    op.create_index("ix_inbound_mailbox_message_id", "inbound_recruiter_messages", ["mailbox_id", "message_id"])
    op.create_index("ix_inbound_mailbox_received", "inbound_recruiter_messages", ["mailbox_id", "received_at"])


def downgrade() -> None:
    op.drop_index("ix_inbound_mailbox_received", table_name="inbound_recruiter_messages")
    op.drop_index("ix_inbound_mailbox_message_id", table_name="inbound_recruiter_messages")
    op.drop_index("ix_chat_conversations_user_updated", table_name="chat_conversations")
    op.drop_index("ix_applications_user_created", table_name="applications")
    op.drop_index("ix_jobs_company_lower", table_name="jobs")
    op.drop_index("ix_jobs_active_fetched_at", table_name="jobs")
