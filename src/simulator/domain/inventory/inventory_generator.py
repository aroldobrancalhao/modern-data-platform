import random

from simulator.domain.inventory.inventory_model import Inventory


class InventoryGenerator:
    def generate(
        self,
        warehouse_id,
        product_id,
    ) -> Inventory:
        available = random.randint(20, 500)
        reserved = random.randint(0, min(available, 20))
        minimum = random.randint(5, 20)

        return Inventory.create(
            warehouse_id=warehouse_id,
            product_id=product_id,
            available_quantity=available,
            reserved_quantity=reserved,
            minimum_quantity=minimum,
        )
