from random import randint

from psycopg import Connection

from simulator.core.batch_writer import BatchWriter
from simulator.core.reference_pool import OrderReference
from simulator.core.reference_pool import ReferencePool
from simulator.core.unique_insert import insert_with_unique_retry
from simulator.domain.inventory.inventory_repository import InventoryRepository
from simulator.domain.inventory.movement_model import InventoryMovement
from simulator.domain.inventory.movement_repository import InventoryMovementRepository
from simulator.domain.orders.order_generator import OrderGenerator
from simulator.domain.orders.order_model import Order
from simulator.domain.orders.order_repository import OrderRepository

MAX_INVENTORY_RESERVE_ATTEMPTS = 5


class OrderService:
    def __init__(self) -> None:
        self._generator = OrderGenerator()

    def create_order(
        self,
        connection: Connection,
        writer: BatchWriter,
        pool: ReferencePool,
    ) -> Order:
        inventory_repository = InventoryRepository(connection)

        customer_id = pool.random_customer_id()

        if customer_id is None:
            raise ValueError("No customer found.")

        inventory_id, product_id, unit_price, quantity = self._reserve_inventory(
            inventory_repository
        )

        order_repository = OrderRepository(connection, writer)
        movement_repository = InventoryMovementRepository(writer)

        order, order_item, history = insert_with_unique_retry(
            "order",
            lambda: self._generator.generate(
                customer_id=customer_id,
                product_id=product_id,
                unit_price=unit_price,
                quantity=quantity,
            ),
            lambda generated: order_repository.insert_order(generated[0]),
        )

        order_repository.insert_order_details(order_item, history)

        movement = InventoryMovement.outbound(
            inventory_id=inventory_id,
            order_id=order.order_id,
            quantity=order_item.quantity,
        )

        movement_repository.insert(movement)

        pool.orders.append(
            OrderReference(
                order_id=order.order_id,
                customer_id=order.customer_id,
                product_id=product_id,
                total_amount=order.total_amount,
            )
        )

        return order

    def _reserve_inventory(
        self,
        inventory_repository: InventoryRepository,
    ):
        """
        Picks a random inventory row and reserves (decreases) a
        quantity that is guaranteed not to exceed what it actually had
        available *at selection time* -- unlike the previous design,
        which rolled a quantity (1-5) with no idea how much stock the
        picked row actually had, and crashed the whole batch the first
        time it rolled more than was left.

        Still retries (rather than trusting the bound quantity blindly)
        because `decrease_available_quantity`'s conditional UPDATE
        remains the real source of truth against concurrent writers;
        this process is single-connection/single-threaded so that
        should never actually fire in practice, but a fresh inventory
        pick + another attempt is cheap insurance against relying on
        that assumption. Gives up loudly, like every other retry loop
        in this codebase, rather than silently limiting order sizes to
        whatever the *first* pick happened to have.
        """
        for attempt in range(1, MAX_INVENTORY_RESERVE_ATTEMPTS + 1):
            inventory = inventory_repository.get_random_inventory()

            if inventory is None:
                raise ValueError("No inventory found.")

            inventory_id, product_id, available_quantity = inventory

            unit_price = inventory_repository.get_product(product_id)

            if unit_price is None:
                raise ValueError("No product price found.")

            quantity = min(randint(1, 5), available_quantity)

            updated = inventory_repository.decrease_available_quantity(
                inventory_id=inventory_id,
                quantity=quantity,
            )

            if updated:
                return inventory_id, product_id, unit_price, quantity

            print(
                f"WARNING: inventory {inventory_id} had insufficient stock "
                f"by the time of reservation (attempt {attempt}/"
                f"{MAX_INVENTORY_RESERVE_ATTEMPTS}) -- picking a different "
                "inventory and retrying."
            )

        raise ValueError(
            f"Could not reserve inventory after "
            f"{MAX_INVENTORY_RESERVE_ATTEMPTS} attempts."
        )
