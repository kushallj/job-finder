"""portfolio_companies.logo_url (scraped company logos for the Founders page)

Revision ID: 5b8e2f4c1d6a
Revises: 3f2d8c1a9b7e
Create Date: 2026-11-09 18:00:00

Filled by the founder importer from data/company_logos.json, which
src/vc_intelligence/logo_scraper.py builds from each company's homepage.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "5b8e2f4c1d6a"
down_revision: Union[str, None] = "3f2d8c1a9b7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("portfolio_companies") as batch:
        batch.add_column(sa.Column("logo_url", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("portfolio_companies") as batch:
        batch.drop_column("logo_url")
