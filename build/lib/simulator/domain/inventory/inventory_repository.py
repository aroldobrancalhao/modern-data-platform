from uuid import UUID

from psycopg import Connection

from simulator.domain.inventory.inventory_model import Inventory


class InventoryRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, inventory: Inventory) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO marketplace.inventories
                (
                    inventory_id,
                    warehouse_id,
                    product_id,
                    available_quantity,
                    reserved_quantity,
                    minimum_quantity,
                    updated_at
                )
                VALUES
                (
                    %s,%s,%s,%s,%s,%s,%s
                )
                ON CONFLICT (warehouse_id, product_id)
                DO NOTHING
                RETURNING inventory_id
                """,
                (
                    inventory.inventory_id,
                    inventory.warehouse_id,
                    inventory.product_id,
                    inventory.available_quantity,
                    inventory.reserved_quantity,
                    inventory.minimum_quantity,
                    inventory.updated_at,
                ),
            )

        self._connection.commit()

    def decrease_available_quantity(
        self,
        inventory_id,
        quantity: int,
    ) -> bool:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE marketplace.inventories
                SET available_quantity = available_quantity - %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE inventory_id = %s
                AND available_quantity >= %s
                RETURNING inventory_id
                """,
                (
                    quantity,
                    inventory_id,
                    quantity,
                ),
            )

            return cursor.fetchone() is not None

    def increase_available_quantity(
        self,
        inventory_id,
        quantity: int,
    ) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE marketplace.inventories
                SET available_quantity = available_quantity + %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE inventory_id = %s
                """,
                (
                    quantity,
                    inventory_id,
                ),
            )

    def get_random_inventory(self,) -> tuple[UUID, UUID, int] | None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    inventory_id,
                    product_id,
                    available_quantity
                FROM marketplace.inventories
                WHERE available_quantity > 0
                ORDER BY random()
                LIMIT 1
                """
            )

            return cursor.fetchone()
        
    def get_product(
        self,
        product_id,
    ) -> float | None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT price
                FROM marketplace.products
                WHERE product_id = %s
                """,
                (product_id,),
            )

            row = cursor.fetchone()

            if row is None:
                return None

            return row[0]