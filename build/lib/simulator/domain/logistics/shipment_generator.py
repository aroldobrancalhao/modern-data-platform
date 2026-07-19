from datetime import UTC
from datetime import datetime
from datetime import timedelta
from random import choices
from uuid import UUID

from faker import Faker

from simulator.domain.logistics.shipment_model import Shipment


class ShipmentGenerator:

    _STATUS = (
        "DELIVERED",
        "IN_TRANSIT",
        "SHIPPED",
        "CREATED",
        "RETURNED",
    )

    _STATUS_WEIGHTS = (
        70,
        20,
        7,
        2,
        1,
    )

    def __init__(self) -> None:
        self._faker = Faker("pt_BR")

    def generate(
        self,
        order_id: UUID,
        carrier_id: UUID,
    ) -> Shipment:

        now = datetime.now(UTC)

        status = choices(
            self._STATUS,
            weights=self._STATUS_WEIGHTS,
            k=1,
        )[0]

        shipped_at = None
        estimated_delivery = None
        delivered_at = None

        if status != "CREATED":
            shipped_at = now

        if status in (
            "SHIPPED",
            "IN_TRANSIT",
            "DELIVERED",
        ):
            estimated_delivery = now + timedelta(
                days=self._faker.random_int(2, 10)
            )

        if status == "DELIVERED":
            delivered_at = estimated_delivery

        return Shipment.create(
            order_id=order_id,
            carrier_id=carrier_id,
            tracking_code=self._faker.unique.bothify(
                "BR##################"
            ),
            status=status,
            shipped_at=shipped_at,
            estimated_delivery_at=estimated_delivery,
            delivered_at=delivered_at,
        )