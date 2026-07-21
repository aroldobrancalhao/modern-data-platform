from simulator.core.database import Database

from simulator.domain.logistics.shipment_generator import ShipmentGenerator
from simulator.domain.logistics.shipment_model import Carrier
from simulator.domain.logistics.shipment_model import Shipment
from simulator.domain.logistics.shipment_repository import ShipmentRepository
from simulator.domain.orders.order_repository import OrderRepository


class ShipmentService:
    CARRIERS = (
        ("CORREIOS", "Correios"),
        ("LOGGI", "Loggi"),
        ("JADLOG", "Jadlog"),
        ("DHL", "DHL"),
        ("AZUL", "Azul Cargo"),
    )

    def __init__(self) -> None:
        self._database = Database()
        self._generator = ShipmentGenerator()

    def create_shipment(self) -> Shipment:

        with self._database.connection() as connection:
            repository = ShipmentRepository(connection)

            for code, name in self.CARRIERS:
                repository.create_carrier(
                    Carrier.create(
                        code=code,
                        name=name,
                        phone_number=None,
                        email=None,
                    )
                )

            carrier_id = repository.get_random_carrier()

            if carrier_id is None:
                raise ValueError("No carrier found.")

            order_repository = OrderRepository(connection)

            order = order_repository.get_random_order()

            if order is None:
                raise ValueError("No order found.")

            order_id, _, _, _ = order

            shipment = self._generator.generate(
                order_id=order_id,
                carrier_id=carrier_id,
            )

            repository.create_shipment(shipment)

            return shipment
