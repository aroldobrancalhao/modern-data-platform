from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from uuid import UUID
from uuid import uuid4


@dataclass(slots=True)
class InventoryMovement:
    movement_id: UUID
    inventory_id: UUID
    movement_type: str
    quantity: int
    reason: str
    created_at: datetime
    order_id: UUID

    @classmethod
    def outbound(
        cls,
        inventory_id: UUID,
        order_id: UUID,
        quantity: int,
    ) -> "InventoryMovement":
        return cls(
            movement_id=uuid4(),
            inventory_id=inventory_id,
            movement_type="OUTBOUND",
            quantity=quantity,
            reason=f"Order {order_id}",
            created_at=datetime.now(UTC),
            order_id=order_id,
        )
