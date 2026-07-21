from dataclasses import dataclass
from datetime import UTC
from datetime import date
from datetime import datetime
from uuid import UUID
from uuid import uuid4


@dataclass(slots=True)
class Customer:
    customer_id: UUID
    first_name: str
    last_name: str
    email: str
    phone_number: str
    document_number: str
    birth_date: date
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        first_name: str,
        last_name: str,
        email: str,
        phone_number: str,
        document_number: str,
        birth_date: date,
    ) -> "Customer":
        now = datetime.now(UTC)

        return cls(
            customer_id=uuid4(),
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone_number=phone_number,
            document_number=document_number,
            birth_date=birth_date,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
