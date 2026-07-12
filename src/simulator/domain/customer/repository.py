from uuid import UUID

from psycopg import Connection

from simulator.domain.customer.model import Customer


class CustomerRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, customer: Customer) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO marketplace.customers (
                    customer_id,
                    first_name,
                    last_name,
                    email,
                    phone_number,
                    document_number,
                    birth_date,
                    is_active,
                    created_at,
                    updated_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    customer.customer_id,
                    customer.first_name,
                    customer.last_name,
                    customer.email,
                    customer.phone_number,
                    customer.document_number,
                    customer.birth_date,
                    customer.is_active,
                    customer.created_at,
                    customer.updated_at,
                ),
            )

        self._connection.commit()

    def get_random_id(self) -> UUID | None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT customer_id
                FROM marketplace.customers
                ORDER BY random()
                LIMIT 1
                """
            )

            row = cursor.fetchone()

        return row[0] if row else None