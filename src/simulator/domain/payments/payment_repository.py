from simulator.core.batch_writer import BatchWriter
from simulator.domain.payments.payment_model import Payment


class PaymentRepository:
    def __init__(self, writer: BatchWriter) -> None:
        self._writer = writer

    def create_payment(
        self,
        payment: Payment,
    ) -> None:
        self._writer.add(
            "marketplace.payments",
            (
                "payment_id",
                "order_id",
                "payment_method_id",
                "transaction_code",
                "amount",
                "status",
                "authorized_at",
                "paid_at",
                "created_at",
                "updated_at",
            ),
            (
                payment.payment_id,
                payment.order_id,
                payment.payment_method_id,
                payment.transaction_code,
                payment.amount,
                payment.status,
                payment.authorized_at,
                payment.paid_at,
                payment.created_at,
                payment.updated_at,
            ),
        )
