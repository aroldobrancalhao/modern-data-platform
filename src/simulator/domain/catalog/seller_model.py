from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from uuid import UUID, uuid4


@dataclass(slots=True)
class Seller:
    seller_id: UUID
    company_name: str
    trade_name: str | None
    document_number: str
    email: str
    phone_number: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        company_name: str,
        trade_name: str | None,
        document_number: str,
        email: str,
        phone_number: str | None,
    ) -> "Seller":
        now = datetime.now(UTC)

        return cls(
            seller_id=uuid4(),
            company_name=company_name,
            trade_name=trade_name,
            document_number=document_number,
            email=email,
            phone_number=phone_number,
            is_active=True,
            created_at=now,
            updated_at=now,
        )


@dataclass(slots=True)
class Category:
    category_id: UUID
    parent_category_id: UUID | None
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        name: str,
        description: str | None,
        parent_category_id: UUID | None = None,
    ) -> "Category":
        now = datetime.now(UTC)

        return cls(
            category_id=uuid4(),
            parent_category_id=parent_category_id,
            name=name,
            description=description,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
