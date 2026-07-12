from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from uuid import UUID
from uuid import uuid4


@dataclass(slots=True)
class Inventory:
    inventory_id: UUID
    warehouse_id: UUID
    product_id: UUID
    available_quantity: int
    reserved_quantity: int
    minimum_quantity: int
    updated_at: datetime

    @classmethod
    def create(
        cls,
        warehouse_id: UUID,
        product_id: UUID,
        available_quantity: int,
        reserved_quantity: int,
        minimum_quantity: int,
    ) -> "Inventory":
        return cls(
            inventory_id=uuid4(),
            warehouse_id=warehouse_id,
            product_id=product_id,
            available_quantity=available_quantity,
            reserved_quantity=reserved_quantity,
            minimum_quantity=minimum_quantity,
            updated_at=datetime.now(UTC),
        )