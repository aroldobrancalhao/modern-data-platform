from simulator.core.database import Database

from simulator.domain.catalog.product_repository import ProductRepository
from simulator.domain.customer.repository import CustomerRepository
from simulator.domain.orders.order_generator import OrderGenerator
from simulator.domain.orders.order_model import Order
from simulator.domain.orders.order_repository import OrderRepository


class OrderService:
    def __init__(self) -> None:
        self._database = Database()
        self._generator = OrderGenerator()

    def create_order(self) -> Order:
        with self._database.connection() as connection:
            customer_repository = CustomerRepository(connection)
            product_repository = ProductRepository(connection)

            customer_id = customer_repository.get_random_id()
            product = product_repository.get_random_product()

            if customer_id is None:
                raise ValueError("No customer found.")

            if product is None:
                raise ValueError("No product found.")

            product_id, unit_price = product

            order, order_item, history = self._generator.generate(
                customer_id=customer_id,
                product_id=product_id,
                unit_price=unit_price,
            )

            repository = OrderRepository(connection)

            repository.create_order(
                order=order,
                order_item=order_item,
                history=history,
            )

            return order