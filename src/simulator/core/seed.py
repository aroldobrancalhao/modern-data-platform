"""
One-time reference-data seeding.

payment_methods/carriers: before this, every single `create_payment()`/
`create_shipment()` call re-inserted all 5 payment methods / 5 carriers,
relying on `ON CONFLICT DO NOTHING` to make every call after the first a
no-op -- correct, but ~10 wasted round trips per cycle for data that
never changes.

categories: a real duplication bug, not just a perf one -- `category_id`
is a fresh uuid4() every call, and `categories.name` has no UNIQUE
constraint, so `CategoryService.create_category()` calling this once per
cycle (the same "every call re-inserts" shape as payment_methods/
carriers before their fix) created a brand new row every cycle instead
of reusing one of the 10 real categories. Confirmed against real data:
134,207 rows, only 10 distinct names.

All three are seeded once, immediately, before the cycle loop starts;
their real ids (whether just inserted or already present from an
earlier run) are fetched back into the ReferencePool.
"""

from uuid import UUID

from psycopg import Connection

from simulator.domain.catalog.seller_model import Category
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

CATEGORIES: tuple[str, ...] = (
    "Electronics",
    "Home & Kitchen",
    "Computers",
    "Fashion",
    "Sports",
    "Health",
    "Beauty",
    "Automotive",
    "Books",
    "Toys",
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


def seed_categories(connection: Connection) -> list[UUID]:
    """
    Unlike payment_methods/carriers, `categories` has no UNIQUE
    constraint on `name` (see CategoryRepository's old ON CONFLICT DO
    NOTHING, which never had anything to conflict on) -- adding one
    now would need cleaning up the ~134k duplicate rows that bug
    already produced, out of scope for this fix. Check-then-insert per
    name instead of ON CONFLICT DO NOTHING: same "idempotent across
    runs" result without touching the schema or existing data.
    """
    ids: list[UUID] = []

    with connection.cursor() as cursor:
        for name in CATEGORIES:
            cursor.execute(
                "SELECT category_id FROM marketplace.categories WHERE name = %s LIMIT 1",
                (name,),
            )

            row = cursor.fetchone()

            if row is not None:
                ids.append(row[0])
                continue

            category = Category.create(
                name=name,
                description=f"{name} products",
            )

            cursor.execute(
                """
                INSERT INTO marketplace.categories
                (category_id, parent_category_id, name, description, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    category.category_id,
                    category.parent_category_id,
                    category.name,
                    category.description,
                    category.is_active,
                    category.created_at,
                    category.updated_at,
                ),
            )

            ids.append(category.category_id)

    connection.commit()

    return ids
