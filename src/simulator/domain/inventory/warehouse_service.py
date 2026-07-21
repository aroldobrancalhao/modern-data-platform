from simulator.core.database import Database

from simulator.domain.inventory.warehouse_generator import WarehouseGenerator
from simulator.domain.inventory.warehouse_model import Warehouse
from simulator.domain.inventory.warehouse_repository import WarehouseRepository


class WarehouseService:
    def __init__(self) -> None:
        self._database = Database()
        self._generator = WarehouseGenerator()

    def create_warehouse(self) -> Warehouse:
        warehouse = self._generator.generate()

        with self._database.connection() as connection:
            repository = WarehouseRepository(connection)
            repository.insert(warehouse)

        return warehouse
