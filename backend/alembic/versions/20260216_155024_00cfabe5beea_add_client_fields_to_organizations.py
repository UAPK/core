"""add_client_fields_to_organizations

Revision ID: 00cfabe5beea
Revises: 7bced6ee1e55
Create Date: 2026-02-16 15:50:24.234316+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '00cfabe5beea'
down_revision: Union[str, None] = '7bced6ee1e55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add client management fields to organizations table
    op.add_column('organizations', sa.Column('billing_email', sa.String(length=255), nullable=True))
    op.add_column('organizations', sa.Column('contact_name', sa.String(length=255), nullable=True))
    op.add_column('organizations', sa.Column('contact_email', sa.String(length=255), nullable=True))
    op.add_column('organizations', sa.Column('company_address', sa.String(length=500), nullable=True))
    op.add_column('organizations', sa.Column('vat_id', sa.String(length=50), nullable=True))
    op.add_column('organizations', sa.Column('country_code', sa.String(length=2), nullable=True))
    op.add_column('organizations', sa.Column('payment_terms_days', sa.Integer(), nullable=False, server_default='30'))
    op.add_column('organizations', sa.Column('currency', sa.String(length=3), nullable=False, server_default='EUR'))


def downgrade() -> None:
    # Remove client management fields from organizations table
    op.drop_column('organizations', 'currency')
    op.drop_column('organizations', 'payment_terms_days')
    op.drop_column('organizations', 'country_code')
    op.drop_column('organizations', 'vat_id')
    op.drop_column('organizations', 'company_address')
    op.drop_column('organizations', 'contact_email')
    op.drop_column('organizations', 'contact_name')
    op.drop_column('organizations', 'billing_email')
