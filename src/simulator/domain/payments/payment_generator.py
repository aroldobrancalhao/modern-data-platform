from datetime import UTC
from datetime import datetime
from decimal import Decimal
from random import choices
from uuid import UUID
from uuid import uuid4

from faker import Faker

from simulator.core.faker_fallback import unique_or_fallback
from simulator.domain.payments.payment_model import Payment


class PaymentGenerator:
    _PAYMENT_STATUS = (
        "PAID",
        "AUTHORIZED",
        "PENDING",
        "FAILED",
        "CANCELLED",
        "REFUNDED",
    )

    _PAYMENT_STATUS_WEIGHTS = (
        75,
        10,
        7,
        5,
        2,
        1,
    )

    def __init__(self) -> None:
        self._faker = Faker()

    def generate(
        self,
        order_id: UUID,
        payment_method_id: UUID,
        amount: Decimal,
    ) -> Payment:

        status = choices(
            self._PAYMENT_STATUS,
            weights=self._PAYMENT_STATUS_WEIGHTS,
            k=1,
        )[0]

        now = datetime.now(UTC)

        authorized_at = None
        paid_at = None

        if status in ("AUTHORIZED", "PAID", "REFUNDED"):
            authorized_at = now

        if status in ("PAID", "REFUNDED"):
            paid_at = now

        return Payment(
            payment_id=self._faker.uuid4(cast_to=None),
            order_id=order_id,
            payment_method_id=payment_method_id,
            transaction_code=unique_or_fallback(
                "payment.transaction_code",
                lambda: self._faker.unique.bothify("TXN################"),
                lambda: f"TXN{uuid4().hex[:16].upper()}",
            ),
            amount=amount,
            status=status,
            authorized_at=authorized_at,
            paid_at=paid_at,
            created_at=now,
            updated_at=now,
        )
