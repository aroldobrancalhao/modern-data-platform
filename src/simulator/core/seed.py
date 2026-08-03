"""
One-time reference-data seeding.

Before this change, every single `create_payment()`/`create_shipment()`
call re-inserted all 5 payment methods / 5 carriers, relying on
`ON CONFLICT DO NOTHING` to make every call after the first a no-op --
correct, but ~10 wasted round trips per cycle for data that never
changes. Seeded once, immediately, before the cycle loop starts;
their real IDs (whether just inserted or already present from an
earlier run) are fetched back into the ReferencePool.
"""

from uuid import UUID

from psycopg import Connection

from simulator.domain.logistics.shipment_model import Carrier
from simulator.domain.payments.payment_model import PaymentMethod

PAYMENT_METHODS: tuple[tuple[str, str], ...] = (
    ("PIX", "Pix"),
    ("CREDIT_CARD", "Credit Card"),
    ("DEBIT_CARD", "Debit Card"),
    ("BOLETO", "Boleto"),
    ("WALLET", "Digital Wallet"),
)

CARRIERS: tuple[tuple[str, str], ...] = (
    ("CORREIOS", "Correios"),
    ("LOGGI", "Loggi"),
    ("JADLOG", "Jadlog"),
    ("DHL", "DHL"),
    ("AZUL", "Azul Cargo"),
)


def seed_payment_methods(connection: Connection) -> list[UUID]:
    with connection.cursor() as cursor:
        for code, name in PAYMENT_METHODS:
            method = PaymentMethod.create(code=code, name=name)

            cursor.execute(
                """
                INSERT INTO marketplace.payment_methods
                (payment_method_id, code, name, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (code) DO NOTHING
                """,
                (
                    method.payment_method_id,
                    method.code,
                    method.name,
                    method.is_active,
                    method.created_at,
                    method.updated_at,
                ),
            )

        cursor.execute("SELECT payment_method_id FROM marketplace.payment_methods")

        ids = [row[0] for row in cursor.fetchall()]

    connection.commit()

    return ids


def seed_carriers(connection: Connection) -> list[UUID]:
    with connection.cursor() as cursor:
        for code, name in CARRIERS:
            carrier = Carrier.create(
                code=code,
                name=name,
                phone_number=None,
                email=None,
            )

            cursor.execute(
                """
                INSERT INTO marketplace.carriers
                (carrier_id, code, name, phone_number, email, is_active, created_at, updated_at, deleted_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (code) DO NOTHING
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

        cursor.execute(
            "SELECT carrier_id FROM marketplace.carriers WHERE is_active = TRUE"
        )

        ids = [row[0] for row in cursor.fetchall()]

    connection.commit()

    return ids
