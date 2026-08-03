from simulator.core.batch_writer import BatchWriter
from simulator.domain.logistics.shipment_model import Shipment


class ShipmentRepository:
    def __init__(self, writer: BatchWriter) -> None:
        self._writer = writer

    def create_shipment(
        self,
        shipment: Shipment,
    ) -> None:
        self._writer.add(
            "marketplace.shipments",
            (
                "shipment_id",
                "order_id",
                "carrier_id",
                "tracking_code",
                "status",
                "shipped_at",
                "estimated_delivery_at",
                "delivered_at",
                "created_at",
                "updated_at",
            ),
            (
                shipment.shipment_id,
                shipment.order_id,
                shipment.carrier_id,
                shipment.tracking_code,
                shipment.status,
                shipment.shipped_at,
                shipment.estimated_delivery_at,
                shipment.delivered_at,
                shipment.created_at,
                shipment.updated_at,
            ),
        )
