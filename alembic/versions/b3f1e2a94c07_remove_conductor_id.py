"""remove conductor_id from performance and set_list_entry

Revision ID: b3f1e2a94c07
Revises: 6a709b7ef3a2
Create Date: 2026-05-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3f1e2a94c07'
down_revision: Union[str, Sequence[str], None] = 'e5be780fa5b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('performance_conductor_id_fkey', 'performance', type_='foreignkey')
    op.drop_column('performance', 'conductor_id')
    op.drop_constraint('set_list_entry_conductor_id_fkey', 'set_list_entry', type_='foreignkey')
    op.drop_column('set_list_entry', 'conductor_id')


def downgrade() -> None:
    op.add_column('set_list_entry', sa.Column('conductor_id', sa.String(), nullable=True))
    op.create_foreign_key(None, 'set_list_entry', 'performer', ['conductor_id'], ['id'])
    op.add_column('performance', sa.Column('conductor_id', sa.String(), nullable=True))
    op.create_foreign_key(None, 'performance', 'performer', ['conductor_id'], ['id'])
