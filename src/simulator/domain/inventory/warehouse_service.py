from psycopg import Connection

from simulator.domain.inventory.warehouse_generator import WarehouseGenerator
from simulator.domain.inventory.warehouse_model import Warehouse
from simulator.domain.inventory.warehouse_repository import WarehouseRepository


class WarehouseService:
    def __init__(self) -> None:
        self._generator = WarehouseGenerator()

    def create_warehouse(self, connection: Connection) -> Warehouse:
        warehouse = self._generator.generate()

        repository = WarehouseRepository(connection)
        repository.insert(warehouse)

        return warehouse
