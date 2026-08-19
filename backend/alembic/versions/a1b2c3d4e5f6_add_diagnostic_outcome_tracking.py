"""add diagnostic outcome tracking

Revision ID: a1b2c3d4e5f6
Revises: 9d4f2a1b3c8e
Create Date: 2026-08-19 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '9d4f2a1b3c8e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE diagnostic_results
        ADD COLUMN IF NOT EXISTS hypothesis_status VARCHAR(20) NOT NULL DEFAULT 'proposed'
    """)
    op.execute("""
        ALTER TABLE diagnostic_results
        ADD COLUMN IF NOT EXISTS observed_result TEXT
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_diagnostic_results_hypothesis_status
        ON diagnostic_results (hypothesis_status)
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS diagnostic_check_outcomes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            result_id UUID NOT NULL REFERENCES diagnostic_results(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            check_description TEXT NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'recommended',
            observed_result TEXT,
            technician_note TEXT
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_diagnostic_check_outcomes_result_id
        ON diagnostic_check_outcomes (result_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_diagnostic_check_outcomes_status
        ON diagnostic_check_outcomes (status)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_diagnostic_check_outcomes_status")
    op.execute("DROP INDEX IF EXISTS ix_diagnostic_check_outcomes_result_id")
    op.execute("DROP TABLE IF EXISTS diagnostic_check_outcomes")
    op.execute("DROP INDEX IF EXISTS ix_diagnostic_results_hypothesis_status")
    op.execute("ALTER TABLE diagnostic_results DROP COLUMN IF EXISTS observed_result")
    op.execute("ALTER TABLE diagnostic_results DROP COLUMN IF EXISTS hypothesis_status")
