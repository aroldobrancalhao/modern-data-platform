from dataclasses import dataclass
from dataclasses import field
from decimal import Decimal
from random import choice
from uuid import UUID


@dataclass(slots=True)
class OrderReference:
    order_id: UUID
    customer_id: UUID
    product_id: UUID
    total_amount: Decimal


@dataclass(slots=True)
class ReferencePool:
    """
    In-memory pool of IDs generated so far in this process, used to
    pick a random existing parent for a new row without querying
    Postgres -- avoids the full-table scan + sort `ORDER BY random()`
    does on every call, which only gets worse as tables grow into the
    hundreds of thousands of rows.

    Sellers, categories, customers, products and orders are written
    immediately and synchronously, with an `INSERT ... RETURNING`
    check confirming the row actually landed before its id is appended
    here (see `unique_insert.py`) -- so despite being in-memory, every
    id in this pool is guaranteed to already exist in Postgres, not
    just "generated and expected to land eventually". This is what
    closes a real bug: a plain `ON CONFLICT DO NOTHING` insert can
    silently no-op when a generated unique field (email, document
    number, sku, order number, ...) collides with a row already
    persisted from a *previous* process run -- Faker's own `.unique`
    tracking has no idea what is already in Postgres. Without the
    RETURNING check, this pool (and anything buffered downstream that
    trusts it, e.g. `customer_addresses`, `order_items`) could hold an
    id that was never actually written, producing a FK violation
    later at flush time.

    Deliberately excludes warehouses/inventory: those stay on
    immediate, unbuffered writes with their existing `get_random_*`
    repository queries against the real database (see BatchWriter's
    docstring) -- untouched, since nothing downstream trusts an
    unconfirmed warehouse/inventory id via this pool.
    """

    seller_ids: list[UUID] = field(default_factory=list)
    category_ids: list[UUID] = field(default_factory=list)
    customer_ids: list[UUID] = field(default_factory=list)
    product_ids: list[UUID] = field(default_factory=list)
    orders: list[OrderReference] = field(default_factory=list)
    payment_method_ids: list[UUID] = field(default_factory=list)
    carrier_ids: list[UUID] = field(default_factory=list)

    def random_seller_id(self) -> UUID | None:
        return choice(self.seller_ids) if self.seller_ids else None

    def random_category_id(self) -> UUID | None:
        return choice(self.category_ids) if self.category_ids else None

    def random_customer_id(self) -> UUID | None:
        return choice(self.customer_ids) if self.customer_ids else None

    def random_product_id(self) -> UUID | None:
        return choice(self.product_ids) if self.product_ids else None

    def random_order(self) -> OrderReference | None:
        return choice(self.orders) if self.orders else None

    def random_payment_method_id(self) -> UUID | None:
        return choice(self.payment_method_ids) if self.payment_method_ids else None

    def random_carrier_id(self) -> UUID | None:
        return choice(self.carrier_ids) if self.carrier_ids else None
