from decimal import Decimal

from simulator.core.database import Database

from simulator.domain.orders.order_repository import OrderRepository
from simulator.domain.payments.payment_generator import PaymentGenerator
from simulator.domain.payments.payment_model import Payment
from simulator.domain.payments.payment_model import PaymentMethod
from simulator.domain.payments.payment_repository import PaymentRepository


class PaymentService:
    PAYMENT_METHODS = (
        ("PIX", "Pix"),
        ("CREDIT_CARD", "Credit Card"),
        ("DEBIT_CARD", "Debit Card"),
        ("BOLETO", "Boleto"),
        ("WALLET", "Digital Wallet"),
    )

    def __init__(self) -> None:
        self._database = Database()
        self._generator = PaymentGenerator()

    def create_payment(self) -> Payment:

        with self._database.connection() as connection:
            repository = PaymentRepository(connection)

            for code, name in self.PAYMENT_METHODS:
                repository.create_payment_method(
                    PaymentMethod.create(
                        code=code,
                        name=name,
                    )
                )

            order_repository = OrderRepository(connection)

            order = order_repository.get_random_order()

            if order is None:
                raise ValueError("No order found.")

            order_id, _, _, amount = order

            payment_method = repository.get_random_payment_method()

            if payment_method is None:
                raise ValueError("No payment method found.")

            payment = self._generator.generate(
                order_id=order_id,
                payment_method_id=payment_method,
                amount=Decimal(amount),
            )

            repository.create_payment(payment)

            return payment
