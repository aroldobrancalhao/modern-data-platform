from psycopg import Connection

from simulator.domain.inventory.movement_model import InventoryMovement


class InventoryMovementRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(
        self,
        movement: InventoryMovement,
    ) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO marketplace.inventory_movements
                (
                    movement_id,
                    inventory_id,
                    movement_type,
                    quantity,
                    reason,
                    created_at,
                    order_id
                )
                VALUES
                (
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
                    movement.movement_id,
                    movement.inventory_id,
                    movement.movement_type,
                    movement.quantity,
                    movement.reason,
                    movement.created_at,
                    movement.order_id,
                ),
            )
