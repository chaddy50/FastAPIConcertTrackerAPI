"""make venue osm fields optional

Revision ID: c1d2e3f4a5b6
Revises: b3f1e2a94c07
Create Date: 2026-07-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = 'b3f1e2a94c07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('venue', 'osm_type', existing_type=sa.String(), nullable=True)
    op.alter_column('venue', 'osm_id', existing_type=sa.BigInteger(), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('venue', 'osm_id', existing_type=sa.BigInteger(), nullable=False)
    op.alter_column('venue', 'osm_type', existing_type=sa.String(), nullable=False)
