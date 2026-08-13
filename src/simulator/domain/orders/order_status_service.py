from random import random
from uuid import UUID

from psycopg import Connection

# (next_status, min_age_seconds, probability_per_tick) -- checked once
# per run_batch() tick (see MarketplaceScheduler.run_batch()), not per
# cycle: this walks a bounded number of *existing* orders forward, it
# doesn't create anything, so it has no business running 1000x per
# 5s tick the way an inner-cycle call would.
#
# min_age/probability values and their reasoning: approved design,
# docs/architecture/roadmap-next-steps.md ("progressão de status de
# pedido no simulador"). Mean wait once eligible = tick (5s) /
# probability, e.g. PENDING -> PAID: 5/0.15 ~= 33s after the 60s
# minimum, ~1.5min total on average. Full PENDING -> DELIVERED
# average ~= 15min -- long enough to feel organic across a demo
# session, short enough to actually watch happen.
_FORWARD_RULES: dict[str, tuple[str, float, float]] = {
    "PENDING": ("PAID", 60.0, 0.15),
    "PAID": ("PROCESSING", 120.0, 0.10),
    "PROCESSING": ("SHIPPED", 180.0, 0.08),
    "SHIPPED": ("DELIVERED", 300.0, 0.05),
}

# Cancellation only from these 3 stages -- once physically SHIPPED,
# the real-world equivalent is a return/refund, not a cancellation,
# so that's deliberately out of this service's scope. Uses the same
# stage's own min_age gate above (via find_eligible()) rather than a
# separate age threshold -- no reason to cancel-check an order younger
# than it's even forward-eligible. Weighted toward PENDING (payment
# failure, the most common real cancellation reason), tapering off --
# not a precisely derived aggregate target, ~5% overall by design,
# confirmed empirically after the fact, not solved for in advance.
_CANCEL_PROBABILITY: dict[str, float] = {
    "PENDING": 0.02,
    "PAID": 0.01,
    "PROCESSING": 0.005,
}

# Safety cap, not a tuning knob: bounds how many orders this service
# can ever touch in a single tick per status, regardless of how many
# are actually eligible. Without this, a large backdated backlog
# (e.g. right after a bulk backfill) would all become eligible at
# once and get processed in one burst the first tick the feature is
# live -- this is what actually keeps the trickle a trickle. See the
# backfill entry in docs/architecture/roadmap-next-steps.md for the
# real 138k-order backlog this was designed against.
_CANDIDATES_PER_STATUS_PER_TICK = 15


class OrderStatusRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def find_eligible(
        self,
        status: str,
        min_age_seconds: float,
        limit: int,
    ) -> list[UUID]:
        """
        Oldest-first (``ORDER BY updated_at ASC``), capped at
        ``limit`` -- direct against Postgres, not the in-memory
        ReferencePool (rebuilt empty every run_batch() call, so it
        would never see an order from a previous tick, a previous
        process run, or the backfill). Using the real, durable
        ``orders`` table here is what makes this safe to restart and
        what makes it apply to every order regardless of when it was
        created.

        Intentional side effect: this is a real FIFO queue, not a
        random sample -- a newly-created order can only be picked
        once every older order of the same ``status`` already past
        ``min_age_seconds`` has been. Confirmed live 2026-08-13: with
        a ~25-order residual backlog ahead of them, 170 orders created
        by a trickle test sat at PENDING for the entire ~20min it took
        that backlog to drain, then started progressing normally.
        Expected, not a bug -- just don't be surprised if a
        freshly-created order doesn't advance the moment it crosses
        ``min_age_seconds`` while an older backlog is still queued.
        """
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT order_id
                FROM marketplace.orders
                WHERE status = %s
                AND updated_at <= now() - (%s || ' seconds')::interval
                ORDER BY updated_at ASC
                LIMIT %s
                """,
                (status, min_age_seconds, limit),
            )

            return [row[0] for row in cursor.fetchall()]

    def transition(
        self,
        order_id: UUID,
        previous_status: str,
        new_status: str,
    ) -> bool:
        """
        One real UPDATE on orders.status (conditional on the expected
        previous status, same defensive-guard pattern as
        InventoryRepository.decrease_available_quantity) plus one
        order_status_history row recording the transition -- the pair
        this whole feature exists to produce: a real change for CDC
        to capture, and a durable audit trail of how it got there.
        """
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE marketplace.orders
                SET status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE order_id = %s AND status = %s
                RETURNING order_id
                """,
                (new_status, order_id, previous_status),
            )

            updated = cursor.fetchone() is not None

            if updated:
                cursor.execute(
                    """
                    INSERT INTO marketplace.order_status_history
                    (history_id, order_id, previous_status, current_status, changed_at)
                    VALUES (gen_random_uuid(), %s, %s, %s, CURRENT_TIMESTAMP)
                    """,
                    (order_id, previous_status, new_status),
                )

            return updated


class OrderStatusService:
    """
    Organic status progression for *existing* orders -- PENDING ->
    PAID -> PROCESSING -> SHIPPED -> DELIVERED, with CANCELLED a
    possible branch from the first three stages. Companion to the
    one-time backfill (scripts/backfill_order_status.py) that seeded
    the pre-existing 138k orders with a plausible starting
    distribution -- this is what keeps *new* orders moving forward
    from here on.

    Deliberately separate from OrderService (which only ever creates
    new orders) -- same reasoning as RestockService living apart from
    InventoryService: this reacts to time passing, not to a specific
    cycle's own order.
    """

    def progress_eligible_orders(self, connection: Connection) -> dict[str, int]:
        repository = OrderStatusRepository(connection)

        counts = {"advanced": 0, "cancelled": 0}

        for status, (next_status, min_age_seconds, probability) in _FORWARD_RULES.items():
            candidates = repository.find_eligible(
                status, min_age_seconds, _CANDIDATES_PER_STATUS_PER_TICK
            )

            cancel_probability = _CANCEL_PROBABILITY.get(status, 0.0)

            for order_id in candidates:
                roll = random()

                if roll < cancel_probability:
                    if repository.transition(order_id, status, "CANCELLED"):
                        counts["cancelled"] += 1
                elif roll < cancel_probability + probability:
                    if repository.transition(order_id, status, next_status):
                        counts["advanced"] += 1

        return counts
