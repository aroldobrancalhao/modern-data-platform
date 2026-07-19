from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from uuid import uuid4


@dataclass(slots=True)
class PaymentMethod:
    payment_method_id: UUID
    code: str
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        code: str,
        name: str,
    ) -> "PaymentMethod":
        now = datetime.now(UTC)

        return cls(
            payment_method_id=uuid4(),
            code=code,
            name=name,
            is_active=True,
            created_at=now,
            updated_at=now,
        )


@dataclass(slots=True)
class Payment:
    payment_id: UUID
    order_id: UUID
    payment_method_id: UUID
    transaction_code: str
    amount: Decimal
    status: str
    authorized_at: datetime | None
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        order_id: UUID,
        payment_method_id: UUID,
        transaction_code: str,
        amount: Decimal,
    ) -> "Payment":
        now = datetime.now(UTC)

        return cls(
            payment_id=uuid4(),
            order_id=order_id,
            payment_method_id=payment_method_id,
            transaction_code=transaction_code,
            amount=amount,
            status="PAID",
            authorized_at=now,
            paid_at=now,
            created_at=now,
            updated_at=now,
        )