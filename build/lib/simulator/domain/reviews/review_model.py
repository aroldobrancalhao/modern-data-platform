from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from uuid import UUID
from uuid import uuid4


@dataclass(slots=True)
class Review:
    review_id: UUID
    order_id: UUID
    customer_id: UUID
    product_id: UUID
    rating: int
    title: str | None
    comment: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        order_id: UUID,
        customer_id: UUID,
        product_id: UUID,
        rating: int,
        title: str | None,
        comment: str | None,
    ) -> "Review":

        now = datetime.now(UTC)

        return cls(
            review_id=uuid4(),
            order_id=order_id,
            customer_id=customer_id,
            product_id=product_id,
            rating=rating,
            title=title,
            comment=comment,
            created_at=now,
            updated_at=now,
        )