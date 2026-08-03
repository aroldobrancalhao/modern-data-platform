from psycopg import Connection

from simulator.domain.catalog.seller_model import Seller


class SellerRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, seller: Seller) -> bool:
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
                ON CONFLICT DO NOTHING
                RETURNING seller_id
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

            return cursor.fetchone() is not None
