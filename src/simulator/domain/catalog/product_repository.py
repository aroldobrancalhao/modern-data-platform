from uuid import UUID
from decimal import Decimal

from psycopg import Connection

from simulator.domain.catalog.product_model import Product


class ProductRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, product: Product) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO marketplace.products
                (
                    product_id,
                    seller_id,
                    category_id,
                    sku,
                    name,
                    description,
                    brand,
                    price,
                    weight,
                    height,
                    width,
                    length,
                    status,
                    is_active,
                    created_at,
                    updated_at,
                    deleted_at
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    product.product_id,
                    product.seller_id,
                    product.category_id,
                    product.sku,
                    product.name,
                    product.description,
                    product.brand,
                    product.price,
                    product.weight,
                    product.height,
                    product.width,
                    product.length,
                    product.status,
                    product.is_active,
                    product.created_at,
                    product.updated_at,
                    product.deleted_at,
                ),
            )

        self._connection.commit()

    def get_random_id(self):
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT product_id
                FROM marketplace.products
                ORDER BY random()
                LIMIT 1
                """
            )

            row = cursor.fetchone()

        return row[0] if row else None

    def get_random_product(self) -> tuple[UUID, Decimal] | None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    product_id,
                    price
                FROM marketplace.products
                ORDER BY random()
                LIMIT 1
                """
            )

            row = cursor.fetchone()

        if row is None:
            return None

        return (
            row[0],
            row[1],
        )
