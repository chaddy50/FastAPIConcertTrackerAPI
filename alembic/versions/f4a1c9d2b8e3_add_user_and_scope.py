"""add user and scope

Revision ID: f4a1c9d2b8e3
Revises: b3f1e2a94c07
Create Date: 2026-07-12 00:00:00.000000

Introduces user accounts (API-key auth) and ownership scoping:
- new ``user`` table
- per-user ownership of the personal log (``performance``/``set_list_entry``)
- nullable per-user ownership of *custom* catalog rows (venue/performer/composer/work)
- makes the venue OSM natural key nullable so custom venues can exist

WARNING: this deletes all existing performance / set-list data (they have no
owner and backfill was declined). Take a DB backup before running it.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4a1c9d2b8e3'
down_revision: Union[str, Sequence[str], None] = 'b3f1e2a94c07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CATALOG_TABLES = ("venue", "performer", "composer", "work")


def upgrade() -> None:
    """Upgrade schema."""
    # 1. User table + unique indexes on username and api_key_hash.
    op.create_table(
        "user",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("api_key_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_username", "user", ["username"], unique=True)
    op.create_index("ix_user_api_key_hash", "user", ["api_key_hash"], unique=True)

    # 2. Wipe personal-log rows (no owner; backfill declined). Children first.
    op.execute("DELETE FROM set_list_performer")
    op.execute("DELETE FROM set_list_entry")
    op.execute("DELETE FROM performance_performer")
    op.execute("DELETE FROM performance")

    # 3. Add the NOT NULL owner FKs to the (now empty) personal-log tables.
    op.add_column("performance", sa.Column("user_id", sa.String(), nullable=False))
    op.create_foreign_key("fk_performance_user", "performance", "user", ["user_id"], ["id"])
    op.create_index("ix_performance_user_id", "performance", ["user_id"])

    op.add_column("set_list_entry", sa.Column("user_id", sa.String(), nullable=False))
    op.create_foreign_key("fk_set_list_entry_user", "set_list_entry", "user", ["user_id"], ["id"])
    op.create_index("ix_set_list_entry_user_id", "set_list_entry", ["user_id"])

    # 4. Add the nullable owner FK to each catalog table. Existing rows stay
    #    NULL (= shared/global); only custom rows get an owner going forward.
    for table in _CATALOG_TABLES:
        op.add_column(table, sa.Column("user_id", sa.String(), nullable=True))
        op.create_foreign_key(f"fk_{table}_user", table, "user", ["user_id"], ["id"])
        op.create_index(f"ix_{table}_user_id", table, ["user_id"])

    # 5. Relax the venue OSM columns to nullable (custom venues have no OSM id).
    #    uq_venue_osm stays valid: in Postgres, NULLs are distinct.
    op.alter_column("venue", "osm_type", existing_type=sa.String(), nullable=True)
    op.alter_column("venue", "osm_id", existing_type=sa.BigInteger(), nullable=True)


def downgrade() -> None:
    """Downgrade schema.

    Re-tightens the venue OSM columns to NOT NULL (fails if any custom venues
    exist) and drops all ownership scoping and the user table. Deleted
    personal-log data is not recoverable.
    """
    op.alter_column("venue", "osm_id", existing_type=sa.BigInteger(), nullable=False)
    op.alter_column("venue", "osm_type", existing_type=sa.String(), nullable=False)

    for table in _CATALOG_TABLES:
        op.drop_index(f"ix_{table}_user_id", table_name=table)
        op.drop_constraint(f"fk_{table}_user", table, type_="foreignkey")
        op.drop_column(table, "user_id")

    op.drop_index("ix_set_list_entry_user_id", table_name="set_list_entry")
    op.drop_constraint("fk_set_list_entry_user", "set_list_entry", type_="foreignkey")
    op.drop_column("set_list_entry", "user_id")

    op.drop_index("ix_performance_user_id", table_name="performance")
    op.drop_constraint("fk_performance_user", "performance", type_="foreignkey")
    op.drop_column("performance", "user_id")

    op.drop_index("ix_user_api_key_hash", table_name="user")
    op.drop_index("ix_user_username", table_name="user")
    op.drop_table("user")
