from psycopg import Connection

from simulator.domain.customer.address_model import CustomerAddress


class CustomerAddressRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(
        self,
        address: CustomerAddress,
    ) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO marketplace.customer_addresses
                (
                    address_id,
                    customer_id,
                    address_type,
                    street,
                    street_number,
                    complement,
                    district,
                    city,
                    state,
                    country,
                    postal_code,
                    is_default,
                    created_at,
                    updated_at
                )
                VALUES
                (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
                ON CONFLICT DO NOTHING
                RETURNING address_id
                """,
                (
                    address.address_id,
                    address.customer_id,
                    address.address_type,
                    address.street,
                    address.street_number,
                    address.complement,
                    address.district,
                    address.city,
                    address.state,
                    address.country,
                    address.postal_code,
                    address.is_default,
                    address.created_at,
                    address.updated_at,
                ),
            )

        self._connection.commit()
