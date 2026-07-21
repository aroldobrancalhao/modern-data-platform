from uuid import UUID

from psycopg import Connection

from simulator.domain.logistics.shipment_model import (
    Carrier,
    Shipment,
)


class ShipmentRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def create_carrier(
        self,
        carrier: Carrier,
    ) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO marketplace.carriers
                (
                    carrier_id,
                    code,
                    name,
                    phone_number,
                    email,
                    is_active,
                    created_at,
                    updated_at,
                    deleted_at
                )
                VALUES
                (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s
                )
                ON CONFLICT (code)
                DO NOTHING
                """,
                (
                    carrier.carrier_id,
                    carrier.code,
                    carrier.name,
                    carrier.phone_number,
                    carrier.email,
                    carrier.is_active,
                    carrier.created_at,
                    carrier.updated_at,
                    carrier.deleted_at,
                ),
            )

        self._connection.commit()

    def get_random_carrier(self) -> UUID | None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT carrier_id
                FROM marketplace.carriers
                WHERE is_active = TRUE
                ORDER BY random()
                LIMIT 1
                """
            )

            row = cursor.fetchone()

        return row[0] if row else None

    def create_shipment(
        self,
        shipment: Shipment,
    ) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO marketplace.shipments
                (
                    shipment_id,
                    order_id,
                    carrier_id,
                    tracking_code,
                    status,
                    shipped_at,
                    estimated_delivery_at,
                    delivered_at,
                    created_at,
                    updated_at
                )
                VALUES
                (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                )
                """,
                (
                    shipment.shipment_id,
                    shipment.order_id,
                    shipment.carrier_id,
                    shipment.tracking_code,
                    shipment.status,
                    shipment.shipped_at,
                    shipment.estimated_delivery_at,
                    shipment.delivered_at,
                    shipment.created_at,
                    shipment.updated_at,
                ),
            )

        self._connection.commit()
