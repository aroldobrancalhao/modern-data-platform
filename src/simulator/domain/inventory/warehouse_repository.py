from uuid import UUID

from psycopg import Connection

from simulator.domain.inventory.warehouse_model import Warehouse


class WarehouseRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, warehouse: Warehouse) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO marketplace.warehouses
                (
                    warehouse_id,
                    code,
                    name,
                    street,
                    city,
                    state,
                    country,
                    is_active,
                    created_at,
                    updated_at,
                    deleted_at
                )
                VALUES
                (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                )
                """,
                (
                    warehouse.warehouse_id,
                    warehouse.code,
                    warehouse.name,
                    warehouse.street,
                    warehouse.city,
                    warehouse.state,
                    warehouse.country,
                    warehouse.is_active,
                    warehouse.created_at,
                    warehouse.updated_at,
                    warehouse.deleted_at,
                ),
            )

        self._connection.commit()

    def get_random_id(self) -> UUID | None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT warehouse_id
                FROM marketplace.warehouses
                ORDER BY random()
                LIMIT 1
                """
            )

            row = cursor.fetchone()

        return row[0] if row else None