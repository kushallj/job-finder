"""jobify portfolios

Revision ID: 7c1e5a9d2b40
Revises: 0cfaaf003618
Create Date: 2026-11-07 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c1e5a9d2b40'
down_revision: Union[str, None] = '0cfaaf003618'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('portfolios',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=24), nullable=True),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('published_content', sa.Text(), nullable=True),
    sa.Column('snapshot_at', sa.DateTime(), nullable=True),
    sa.Column('published_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_portfolios_user_id'), 'portfolios', ['user_id'], unique=True)
    op.create_index(op.f('ix_portfolios_username'), 'portfolios', ['username'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_portfolios_username'), table_name='portfolios')
    op.drop_index(op.f('ix_portfolios_user_id'), table_name='portfolios')
    op.drop_table('portfolios')
