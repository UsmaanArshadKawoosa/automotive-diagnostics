"""add knowledge search vector for hybrid retrieval

Revision ID: 9d4f2a1b3c8e
Revises: 61263fa5f6f7
Create Date: 2026-08-19 19:18:30.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9d4f2a1b3c8e'
down_revision: Union[str, Sequence[str], None] = '61263fa5f6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE knowledge_entries
        ADD COLUMN search_vector TSVECTOR
        GENERATED ALWAYS AS (
            setweight(to_tsvector('english', COALESCE(entry_key, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(content, '')), 'B')
        ) STORED
    """)
    op.execute("""
        CREATE INDEX ix_knowledge_entries_search_vector
        ON knowledge_entries USING GIN (search_vector)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_knowledge_entries_search_vector")
    op.execute("ALTER TABLE knowledge_entries DROP COLUMN IF EXISTS search_vector")
