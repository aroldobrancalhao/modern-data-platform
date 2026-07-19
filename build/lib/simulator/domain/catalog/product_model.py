from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from uuid import uuid4


@dataclass(slots=True)
class Product:
    product_id: UUID
    seller_id: UUID
    category_id: UUID
    sku: str
    name: str
    description: str | None
    brand: str | None
    price: Decimal
    weight: Decimal | None
    height: Decimal | None
    width: Decimal | None
    length: Decimal | None
    status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    @classmethod
    def create(
        cls,
        seller_id: UUID,
        category_id: UUID,
        sku: str,
        name: str,
        description: str | None,
        brand: str | None,
        price: Decimal,
        weight: Decimal | None,
        height: Decimal | None,
        width: Decimal | None,
        length: Decimal | None,
    ) -> "Product":
        now = datetime.now(UTC)

        return cls(
            product_id=uuid4(),
            seller_id=seller_id,
            category_id=category_id,
            sku=sku,
            name=name,
            description=description,
            brand=brand,
            price=price,
            weight=weight,
            height=height,
            width=width,
            length=length,
            status="ACTIVE",
            is_active=True,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )