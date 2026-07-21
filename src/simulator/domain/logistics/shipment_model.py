from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from uuid import UUID
from uuid import uuid4


@dataclass(slots=True)
class Carrier:
    carrier_id: UUID
    code: str
    name: str
    phone_number: str | None
    email: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    @classmethod
    def create(
        cls,
        code: str,
        name: str,
        phone_number: str | None,
        email: str | None,
    ) -> "Carrier":
        now = datetime.now(UTC)

        return cls(
            carrier_id=uuid4(),
            code=code,
            name=name,
            phone_number=phone_number,
            email=email,
            is_active=True,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )


@dataclass(slots=True)
class Shipment:
    shipment_id: UUID
    order_id: UUID
    carrier_id: UUID
    tracking_code: str
    status: str
    shipped_at: datetime | None
    estimated_delivery_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        order_id: UUID,
        carrier_id: UUID,
        tracking_code: str,
        status: str,
        shipped_at: datetime | None,
        estimated_delivery_at: datetime | None,
        delivered_at: datetime | None,
    ) -> "Shipment":

        now = datetime.now(UTC)

        return cls(
            shipment_id=uuid4(),
            order_id=order_id,
            carrier_id=carrier_id,
            tracking_code=tracking_code,
            status=status,
            shipped_at=shipped_at,
            estimated_delivery_at=estimated_delivery_at,
            delivered_at=delivered_at,
            created_at=now,
            updated_at=now,
        )
