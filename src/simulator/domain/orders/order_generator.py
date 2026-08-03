from decimal import Decimal
from uuid import UUID
from uuid import uuid4

from faker import Faker

from simulator.core.faker_fallback import unique_or_fallback
from simulator.domain.orders.order_model import (
    Order,
    OrderItem,
    OrderStatusHistory,
)


class OrderGenerator:
    def __init__(self) -> None:
        self._faker = Faker("pt_BR")

    def generate(
        self,
        customer_id: UUID,
        product_id: UUID,
        unit_price: Decimal,
        quantity: int,
    ) -> tuple[Order, OrderItem, OrderStatusHistory]:
        """
        `quantity` is decided by the caller (bounded by real available
        stock, see `OrderService.create_order`), not rolled here --
        this generator no longer has an opinion on how much is being
        bought, only on the order's own fields (order_number, shipping,
        totals derived from the given quantity).
        """
        shipping_amount = Decimal(
            str(
                round(
                    self._faker.pyfloat(
                        min_value=10,
                        max_value=60,
                        right_digits=2,
                    ),
                    2,
                )
            )
        )

        total_amount = unit_price * quantity

        order = Order.create(
            customer_id=customer_id,
            order_number=unique_or_fallback(
                "order.order_number",
                lambda: self._faker.unique.bothify("ORD########"),
                lambda: f"ORD{uuid4().hex[:8].upper()}",
            ),
            total_amount=total_amount,
            shipping_amount=shipping_amount,
        )

        order_item = OrderItem.create(
            order_id=order.order_id,
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
        )

        history = OrderStatusHistory.create(
            order_id=order.order_id,
        )

        return (
            order,
            order_item,
            history,
        )
