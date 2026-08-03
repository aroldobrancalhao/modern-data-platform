from simulator.core.batch_writer import BatchWriter
from simulator.domain.inventory.movement_model import InventoryMovement


class InventoryMovementRepository:
    def __init__(self, writer: BatchWriter) -> None:
        self._writer = writer

    def insert(
        self,
        movement: InventoryMovement,
    ) -> None:
        self._writer.add(
            "marketplace.inventory_movements",
            (
                "movement_id",
                "inventory_id",
                "movement_type",
                "quantity",
                "reason",
                "created_at",
                "order_id",
            ),
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
