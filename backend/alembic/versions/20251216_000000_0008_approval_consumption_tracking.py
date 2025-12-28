"""Add one-time override token consumption tracking.

Revision ID: 0008
Revises: 0007
Create Date: 2025-12-16 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "approvals",
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "approvals",
        sa.Column("consumed_interaction_id", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("approvals", "consumed_interaction_id")
    op.drop_column("approvals", "consumed_at")
