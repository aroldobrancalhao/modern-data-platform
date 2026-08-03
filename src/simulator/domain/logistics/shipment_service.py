from simulator.core.batch_writer import BatchWriter
from simulator.core.reference_pool import ReferencePool
from simulator.domain.logistics.shipment_generator import ShipmentGenerator
from simulator.domain.logistics.shipment_model import Shipment
from simulator.domain.logistics.shipment_repository import ShipmentRepository


class ShipmentService:
    def __init__(self) -> None:
        self._generator = ShipmentGenerator()

    def create_shipment(self, writer: BatchWriter, pool: ReferencePool) -> Shipment:
        order = pool.random_order()

        if order is None:
            raise ValueError("No order found.")

        carrier_id = pool.random_carrier_id()

        if carrier_id is None:
            raise ValueError("No carrier found.")

        shipment = self._generator.generate(
            order_id=order.order_id,
            carrier_id=carrier_id,
        )

        repository = ShipmentRepository(writer)
        repository.create_shipment(shipment)

        return shipment
