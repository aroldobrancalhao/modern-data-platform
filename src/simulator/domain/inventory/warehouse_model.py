from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from uuid import UUID
from uuid import uuid4


@dataclass(slots=True)
class Warehouse:
    warehouse_id: UUID
    code: str
    name: str
    street: str | None
    city: str
    state: str
    country: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    @classmethod
    def create(
        cls,
        code: str,
        name: str,
        street: str | None,
        city: str,
        state: str,
        country: str,
    ) -> "Warehouse":
        now = datetime.now(UTC)

        return cls(
            warehouse_id=uuid4(),
            code=code,
            name=name,
            street=street,
            city=city,
            state=state,
            country=country,
            is_active=True,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )