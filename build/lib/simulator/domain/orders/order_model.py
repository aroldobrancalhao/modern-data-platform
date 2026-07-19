from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from uuid import uuid4


@dataclass(slots=True)
class Order:
    order_id: UUID
    order_number: str
    customer_id: UUID
    status: str
    total_amount: Decimal
    shipping_amount: Decimal
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        customer_id: UUID,
        order_number: str,
        total_amount: Decimal,
        shipping_amount: Decimal,
    ) -> "Order":
        now = datetime.now(UTC)

        return cls(
            order_id=uuid4(),
            order_number=order_number,
            customer_id=customer_id,
            status="PENDING",
            total_amount=total_amount,
            shipping_amount=shipping_amount,
            created_at=now,
            updated_at=now,
        )


@dataclass(slots=True)
class OrderItem:
    order_item_id: UUID
    order_id: UUID
    product_id: UUID
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    created_at: datetime

    @classmethod
    def create(
        cls,
        order_id: UUID,
        product_id: UUID,
        quantity: int,
        unit_price: Decimal,
    ) -> "OrderItem":
        return cls(
            order_item_id=uuid4(),
            order_id=order_id,
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
            total_price=unit_price * quantity,
            created_at=datetime.now(UTC),
        )


@dataclass(slots=True)
class OrderStatusHistory:
    history_id: UUID
    order_id: UUID
    previous_status: str | None
    current_status: str
    changed_at: datetime

    @classmethod
    def create(
        cls,
        order_id: UUID,
    ) -> "OrderStatusHistory":
        return cls(
            history_id=uuid4(),
            order_id=order_id,
            previous_status=None,
            current_status="PENDING",
            changed_at=datetime.now(UTC),
        )