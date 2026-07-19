from decimal import Decimal
from random import randint
from uuid import UUID

from faker import Faker

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
    ) -> tuple[Order, OrderItem, OrderStatusHistory]:

        quantity = randint(1, 5)

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
            order_number=self._faker.unique.bothify("ORD########"),
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