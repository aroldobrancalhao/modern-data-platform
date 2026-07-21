from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from uuid import UUID
from uuid import uuid4


@dataclass(slots=True)
class CustomerAddress:
    address_id: UUID
    customer_id: UUID
    address_type: str
    street: str
    street_number: str
    complement: str | None
    district: str | None
    city: str
    state: str
    country: str
    postal_code: str
    is_default: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        customer_id: UUID,
        street: str,
        street_number: str,
        complement: str | None,
        district: str | None,
        city: str,
        state: str,
        postal_code: str,
    ) -> "CustomerAddress":
        now = datetime.now(UTC)

        return cls(
            address_id=uuid4(),
            customer_id=customer_id,
            address_type="DELIVERY",
            street=street,
            street_number=street_number,
            complement=complement,
            district=district,
            city=city,
            state=state,
            country="Brazil",
            postal_code=postal_code,
            is_default=True,
            created_at=now,
            updated_at=now,
        )
