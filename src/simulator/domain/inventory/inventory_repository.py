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