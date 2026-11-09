"""widen jobs.experience_level to 100 chars

Revision ID: 3f2d8c1a9b7e
Revises: 1c6b3bee659d
Create Date: 2026-11-09 14:00:00

String(20) was too short for real values ("Lead / Staff / Principal" from the crawler,
"Mid-level, Senior" from providers). Postgres rejected those inserts and aborted the
transaction; SQLite never enforced the limit, so tests did not notice. Batch mode keeps
this working on SQLite too.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "3f2d8c1a9b7e"
down_revision: Union[str, None] = "1c6b3bee659d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("jobs") as batch:
        batch.alter_column("experience_level", existing_type=sa.String(length=20), type_=sa.String(length=100),
                           existing_nullable=True)


def downgrade() -> None:
    # Clip first so the narrower type accepts existing rows.
    op.execute("UPDATE jobs SET experience_level = SUBSTR(experience_level, 1, 20) WHERE LENGTH(experience_level) > 20")
    with op.batch_alter_table("jobs") as batch:
        batch.alter_column("experience_level", existing_type=sa.String(length=100), type_=sa.String(length=20),
                           existing_nullable=True)
