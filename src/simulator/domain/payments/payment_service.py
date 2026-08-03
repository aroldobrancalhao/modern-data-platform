from decimal import Decimal

from simulator.core.batch_writer import BatchWriter
from simulator.core.reference_pool import ReferencePool
from simulator.domain.payments.payment_generator import PaymentGenerator
from simulator.domain.payments.payment_model import Payment
from simulator.domain.payments.payment_repository import PaymentRepository


class PaymentService:
    def __init__(self) -> None:
        self._generator = PaymentGenerator()

    def create_payment(self, writer: BatchWriter, pool: ReferencePool) -> Payment:
        order = pool.random_order()

        if order is None:
            raise ValueError("No order found.")

        payment_method_id = pool.random_payment_method_id()

        if payment_method_id is None:
            raise ValueError("No payment method found.")

        payment = self._generator.generate(
            order_id=order.order_id,
            payment_method_id=payment_method_id,
            amount=Decimal(order.total_amount),
        )

        repository = PaymentRepository(writer)
        repository.create_payment(payment)

        return payment
