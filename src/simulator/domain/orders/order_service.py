from simulator.core.database import Database

from simulator.domain.customer.customer_repository import CustomerRepository
from simulator.domain.inventory.inventory_repository import InventoryRepository
from simulator.domain.inventory.movement_model import InventoryMovement
from simulator.domain.inventory.movement_repository import InventoryMovementRepository
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
            inventory_repository = InventoryRepository(connection)

            customer_id = customer_repository.get_random_id()

            if customer_id is None:
                raise ValueError("No customer found.")

            inventory = inventory_repository.get_random_inventory()

            if inventory is None:
                raise ValueError("No inventory found.")

            inventory_id, product_id, _ = inventory

            unit_price = inventory_repository.get_product(product_id)

            if unit_price is None:
                raise ValueError("No product price found.")

            order, order_item, history = self._generator.generate(
                customer_id=customer_id,
                product_id=product_id,
                unit_price=unit_price,
            )

            movement = InventoryMovement.outbound(
                inventory_id=inventory_id,
                order_id=order.order_id,
                quantity=order_item.quantity,
            )

            order_repository = OrderRepository(connection)
            movement_repository = InventoryMovementRepository(connection)

            order_repository.create_order(
                order=order,
                order_item=order_item,
                history=history,
            )

            updated = inventory_repository.decrease_available_quantity(
                inventory_id=inventory_id,
                quantity=order_item.quantity,
            )

            if not updated:
                raise ValueError("Insufficient inventory.")

            movement_repository.insert(movement)

            return order
