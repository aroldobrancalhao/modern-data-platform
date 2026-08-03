from uuid import UUID

from decimal import Decimal

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

    def get_random_inventory(
        self,
    ) -> tuple[UUID, UUID, int] | None:
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

    def get_restock_candidate_id(
        self,
        low_stock_threshold: int,
    ) -> UUID | None:
        """
        Prefers a row already below `low_stock_threshold` (restocking
        the neediest inventory first), falling back to a uniformly
        random one when nothing qualifies -- `(available_quantity <
        threshold) DESC` sorts any qualifying rows first (Postgres
        orders `true` before `false` in `DESC`), `random()` breaks ties
        within whichever group ends up first. One query either way, no
        extra round trip for the common case where a low-stock row
        exists.
        """
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT inventory_id
                FROM marketplace.inventories
                ORDER BY (available_quantity < %s) DESC, random()
                LIMIT 1
                """,
                (low_stock_threshold,),
            )

            row = cursor.fetchone()

        return row[0] if row else None

    def get_product(
        self,
        product_id,
    ) -> Decimal | None:
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
