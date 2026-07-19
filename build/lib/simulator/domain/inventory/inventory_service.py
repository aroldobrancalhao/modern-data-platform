from simulator.core.database import Database

from simulator.domain.catalog.product_repository import ProductRepository
from simulator.domain.inventory.inventory_generator import InventoryGenerator
from simulator.domain.inventory.inventory_model import Inventory
from simulator.domain.inventory.inventory_repository import InventoryRepository
from simulator.domain.inventory.warehouse_repository import WarehouseRepository


class InventoryService:
    def __init__(self) -> None:
        self._database = Database()
        self._generator = InventoryGenerator()

    def create_inventory(self) -> Inventory:
        with self._database.connection() as connection:
            warehouse_repository = WarehouseRepository(connection)
            product_repository = ProductRepository(connection)

            warehouse_id = warehouse_repository.get_random_id()
            product_id = product_repository.get_random_id()

            if warehouse_id is None:
                raise ValueError("No warehouse found.")

            if product_id is None:
                raise ValueError("No product found.")

            inventory = self._generator.generate(
                warehouse_id=warehouse_id,
                product_id=product_id,
            )

            repository = InventoryRepository(connection)
            repository.insert(inventory)

        return inventory