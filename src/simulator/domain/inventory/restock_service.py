from random import randint
from random import random

from psycopg import Connection

from simulator.domain.inventory.inventory_repository import InventoryRepository

LOW_STOCK_THRESHOLD = 20
RESTOCK_MIN = 50
RESTOCK_MAX = 200


class RestockService:
    """
    Periodically replenishes inventory stock, decoupled from any
    specific order -- a warehouse restocks because its own stock ran
    low, not as a reaction to a particular sale, so this stays out of
    OrderService entirely (which should only ever decrease stock).

    Without this, available stock is monotonically decreasing (the
    only other writer of `available_quantity` is `create_inventory`,
    once, at row-creation time): the fraction of thin inventory rows
    climbs for the entire lifetime of a long-running simulation --
    same progressive-degradation shape already seen with
    `warehouse.code` and `customer.email`, just showing up as
    "Insufficient inventory" instead of a uniqueness exception.
    """

    def maybe_restock(self, connection: Connection, probability: float) -> None:
        if random() >= probability:
            return

        repository = InventoryRepository(connection)

        inventory_id = repository.get_restock_candidate_id(LOW_STOCK_THRESHOLD)

        if inventory_id is None:
            return

        quantity = randint(RESTOCK_MIN, RESTOCK_MAX)

        repository.increase_available_quantity(
            inventory_id=inventory_id,
            quantity=quantity,
        )

        print(f"Inventory restocked: {inventory_id} (+{quantity})")
