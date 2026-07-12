from psycopg import Connection

from simulator.domain.orders.order_model import (
    Order,
    OrderItem,
    OrderStatusHistory,
)


class OrderRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def create_order(
        self,
        order: Order,
        order_item: OrderItem,
        history: OrderStatusHistory,
    ) -> None:
        with self._connection.transaction():
            with self._connection.cursor() as cursor:

                cursor.execute(
                    """
                    INSERT INTO marketplace.orders
                    (
                        order_id,
                        order_number,
                        customer_id,
                        status,
                        total_amount,
                        shipping_amount,
                        created_at,
                        updated_at
                    )
                    VALUES
                    (
                        %s,%s,%s,%s,%s,%s,%s,%s
                    )
                    """,
                    (
                        order.order_id,
                        order.order_number,
                        order.customer_id,
                        order.status,
                        order.total_amount,
                        order.shipping_amount,
                        order.created_at,
                        order.updated_at,
                    ),
                )

                cursor.execute(
                    """
                    INSERT INTO marketplace.order_items
                    (
                        order_item_id,
                        order_id,
                        product_id,
                        quantity,
                        unit_price,
                        total_price,
                        created_at
                    )
                    VALUES
                    (
                        %s,%s,%s,%s,%s,%s,%s
                    )
                    """,
                    (
                        order_item.order_item_id,
                        order_item.order_id,
                        order_item.product_id,
                        order_item.quantity,
                        order_item.unit_price,
                        order_item.total_price,
                        order_item.created_at,
                    ),
                )

                cursor.execute(
                    """
                    INSERT INTO marketplace.order_status_history
                    (
                        history_id,
                        order_id,
                        previous_status,
                        current_status,
                        changed_at
                    )
                    VALUES
                    (
                        %s,%s,%s,%s,%s
                    )
                    """,
                    (
                        history.history_id,
                        history.order_id,
                        history.previous_status,
                        history.current_status,
                        history.changed_at,
                    ),
                )