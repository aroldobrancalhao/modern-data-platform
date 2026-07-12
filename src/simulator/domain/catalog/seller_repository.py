from uuid import UUID

from psycopg import Connection

from simulator.domain.catalog.seller_model import Seller


class SellerRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, seller: Seller) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO marketplace.sellers
                (
                    seller_id,
                    company_name,
                    trade_name,
                    document_number,
                    email,
                    phone_number,
                    is_active,
                    created_at,
                    updated_at
                )
                VALUES
                (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s
                )
                """,
                (
                    seller.seller_id,
                    seller.company_name,
                    seller.trade_name,
                    seller.document_number,
                    seller.email,
                    seller.phone_number,
                    seller.is_active,
                    seller.created_at,
                    seller.updated_at,
                ),
            )

        self._connection.commit()

    def get_random_id(self) -> UUID | None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT seller_id
                FROM marketplace.sellers
                ORDER BY random()
                LIMIT 1
                """
            )

            row = cursor.fetchone()

        return row[0] if row else None