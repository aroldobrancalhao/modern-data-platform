from uuid import UUID

from psycopg import Connection

from simulator.domain.catalog.seller_model import Category


class CategoryRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, category: Category) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO marketplace.categories
                (
                    category_id,
                    parent_category_id,
                    name,
                    description,
                    is_active,
                    created_at,
                    updated_at
                )
                VALUES
                (
                    %s,%s,%s,%s,%s,%s,%s
                )
                """,
                (
                    category.category_id,
                    category.parent_category_id,
                    category.name,
                    category.description,
                    category.is_active,
                    category.created_at,
                    category.updated_at,
                ),
            )

        self._connection.commit()

    def get_random_id(self) -> UUID | None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT category_id
                FROM marketplace.categories
                ORDER BY random()
                LIMIT 1
                """
            )

            row = cursor.fetchone()

        return row[0] if row else None