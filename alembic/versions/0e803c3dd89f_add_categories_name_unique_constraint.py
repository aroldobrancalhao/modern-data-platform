"""add categories name unique constraint

categories.name had no UNIQUE constraint, which let
CategoryService.create_category() insert a brand new row every
simulator cycle instead of reusing one of the 10 real categories --
134,207 rows for 10 distinct names, confirmed against real data. Fixed
in application code (seed_categories(), see core/seed.py) and the
existing duplicate rows were consolidated down to 10 in the same
session this constraint was added.

Applied directly against the real database via SQL before Alembic was
adopted (`ALTER TABLE ... ADD CONSTRAINT categories_name_unique UNIQUE
(name)`) -- this migration documents that change for anyone running
`alembic upgrade head` on a fresh database from here on, but on the
database that already exists today it is applied via `alembic stamp`,
never `alembic upgrade`, since the constraint is already there
(re-running the ADD CONSTRAINT would fail with "constraint already
exists").

Revision ID: 0e803c3dd89f
Revises: 4d9f5a49f176
Create Date: 2026-08-03 18:51:41.455195

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0e803c3dd89f'
down_revision: Union[str, Sequence[str], None] = '4d9f5a49f176'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint(
        "categories_name_unique",
        "categories",
        ["name"],
        schema="marketplace",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "categories_name_unique",
        "categories",
        schema="marketplace",
        type_="unique",
    )
