from uuid import UUID

from psycopg import Connection

from simulator.domain.payments.payment_model import Payment, PaymentMethod


class PaymentRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def create_payment_method(
        self,
        payment_method: PaymentMethod,
    ) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO marketplace.payment_methods
                (
                    payment_method_id,
                    code,
                    name,
                    is_active,
                    created_at,
                    updated_at
                )
                VALUES
                (
                    %s,%s,%s,%s,%s,%s
                )
                ON CONFLICT (code)
                DO NOTHING
                """,
                (
                    payment_method.payment_method_id,
                    payment_method.code,
                    payment_method.name,
                    payment_method.is_active,
                    payment_method.created_at,
                    payment_method.updated_at,
                ),
            )

        self._connection.commit()

    def get_random_payment_method(self) -> UUID | None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT payment_method_id
                FROM marketplace.payment_methods
                WHERE is_active = TRUE
                ORDER BY random()
                LIMIT 1
                """
            )

            row = cursor.fetchone()

        return row[0] if row else None

    def create_payment(
        self,
        payment: Payment,
    ) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO marketplace.payments
                (
                    payment_id,
                    order_id,
                    payment_method_id,
                    transaction_code,
                    amount,
                    status,
                    authorized_at,
                    paid_at,
                    created_at,
                    updated_at
                )
                VALUES
                (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                )
                ON CONFLICT (order_id)
                DO NOTHING
                """,
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

        self._connection.commit()