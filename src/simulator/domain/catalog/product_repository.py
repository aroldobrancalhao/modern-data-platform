from psycopg import Connection

from simulator.domain.catalog.product_model import Product


class ProductRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, product: Product) -> bool:
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
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                )
                ON CONFLICT DO NOTHING
                RETURNING product_id
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

            return cursor.fetchone() is not None
