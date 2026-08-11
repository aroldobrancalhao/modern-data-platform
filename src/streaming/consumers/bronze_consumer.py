"""
Modern Data Platform

Bronze Consumer: the streaming half of ADR-0008's flow --

    PostgreSQL -> Debezium -> Kafka -> Bronze Consumer -> BronzeService

-- landing Debezium change events straight into the same Bronze Delta
tables the batch flow writes (``bronze/{entity}/``), via the pure-
Python ``deltalake`` package rather than Spark. This is a deliberate
PoC-scope divergence from ``data_platform.compute.delta_io.write_delta``
(Spark-based, batch-only): pulling Spark into a long-running streaming
process for this project would cost far more than it proves.

Known limitations, accepted for this phase (see project-decisions.md):

- No Dead Letter Queue and no sophisticated retry. A message that
  fails to decode is logged and dropped -- it does not block its
  topic, but it is also not recovered automatically. A micro-batch
  that fails to write to Delta is retried on the next cycle (offsets
  are only committed after a successful write), with no backoff.
- No distributed lock against the batch flow writing the same Delta
  tables concurrently. Accepted as low risk: the Databricks full_pipeline
  Job Bundle has no schedule, so batch only ever runs on a manual
  trigger.
- Deletes are not applied as deletes. Per DebeziumChange's contract,
  a "d" op still carries the row's last known state (via ``before``),
  which this consumer simply appends like any other change -- Bronze
  keeps every version of a row it has ever seen, deleted or not.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

import pyarrow as pa
from deltalake import write_deltalake
from prometheus_client import Counter, Gauge, Histogram

from data_platform.compute.bronze_schema import coerce_record, resolve_bronze_schema
from data_platform.messaging.messaging_provider import MessagingProvider
from data_platform.monitoring.logger import get_logger
from data_platform.storage.config import StorageConfig

from integrations.kafka.messaging.debezium_envelope import decode_debezium_message

logger = get_logger(__name__)

# Module-level (default registry) rather than hook-based like the
# processing framework's PrometheusHook: the Bronze Consumer is a
# long-running process with no pipeline/stage lifecycle to hook into,
# scraped directly by Prometheus (start_http_server, see
# scripts/run_bronze_consumer.py) instead of pushed to the
# Pushgateway.

WRITE_DURATION = Histogram(
    "mdp_bronze_write_duration_seconds",
    "write_deltalake() duration for a Bronze micro-batch flush.",
    labelnames=("entity",),
)

RECORDS_WRITTEN = Counter(
    "mdp_bronze_records_written_total",
    "Records written to a Bronze Delta table.",
    labelnames=("entity",),
)

WRITE_FAILURES = Counter(
    "mdp_bronze_write_failures_total",
    "Bronze micro-batch flushes that failed to write.",
    labelnames=("entity",),
)

MESSAGES_CONSUMED = Counter(
    "mdp_bronze_messages_consumed_total",
    "Debezium messages consumed off Kafka (decoded or not).",
    labelnames=("entity", "topic"),
)

CONSUMER_LAG = Gauge(
    "mdp_bronze_consumer_lag",
    "Consumer lag (unread messages) reported by the MessagingProvider, "
    "as of the last successful flush.",
    labelnames=("entity", "topic"),
)

# Added to measure the before/after effect of the 3 throughput changes
# tracked in docs/architecture/roadmap-next-steps.md ("Bronze
# Consumer's round-robin poll loop is throughput-bound") -- kept
# permanently now that plan is complete (see "Item 2 (parallelize
# flushes) implemented" in that same doc): a genuinely useful
# operational signal -- "how long does one full pass over every topic
# take" -- not just a throwaway measurement tool.
ROUND_DURATION = Histogram(
    "mdp_bronze_round_duration_seconds",
    "Duration of one full round-robin pass over every subscribed topic.",
    buckets=(1, 2.5, 5, 10, 20, 30, 45, 60, 90, 120, 180),
)

_TOPIC_PREFIX = "marketplace.marketplace."

_CONSUMER_GROUP_ID = "bronze-consumer"

_MAX_BATCH_SIZE = 100

# Caps a single consume_batch() call independently of _MAX_BATCH_SIZE
# (the buffer's own flush threshold): 100 messages fetched and
# flushed in one shot, under real backlog, was enough to OOM a fresh
# process before completing even one round-robin pass (confirmed live,
# 3 isolated attempts, all killed by the kernel cgroup OOM killer --
# see docs/architecture/roadmap-next-steps.md). 25 is a quarter of
# _MAX_BATCH_SIZE -- conservative, chosen empirically after 100 failed,
# not derived from a formula. A buffer can still fill up to
# _MAX_BATCH_SIZE across multiple consume_batch() calls in successive
# rounds; this only bounds how much a single call can add at once.
_MAX_POLL_BATCH_SIZE = 25

# products and inventories are the two deepest-backlog entities in the
# Frente 3 reprocess (119,915 and 56,022 messages remaining as of this
# change, vs the next-largest at ~17,600) -- letting either one pull a
# full _MAX_BATCH_SIZE (100) worth of messages in a single
# consume_batch() call, instead of the default _MAX_POLL_BATCH_SIZE
# (25), fills and flushes a buffer in one round-robin turn instead of
# four, directly cutting the number of rounds needed to drain their
# backlog. Every other entity keeps the default 25 cap -- most are
# already at zero lag and would never use the extra room anyway.
#
# Memory headroom, checked live before applying (not assumed): current
# steady RSS 616.8MiB / 1536MiB (40.1%), ~919MiB slack. This override
# does not change _MAX_BATCH_SIZE (the flush threshold, and therefore
# the per-flush write_deltalake() footprint already sized in
# _FLUSH_POOL_SIZE's own comment) -- only how many rounds it takes to
# fill the same 100-record buffer. The only real memory delta is
# transient: up to (100-25)=75 extra raw Kafka message objects
# in-flight per overridden entity in the worst case both are polled
# the same round, i.e. 150 extra messages total vs the previous
# all-25 ceiling. At the ~4.6KB/message figure measured for this same
# workload (see the queued.max.messages.kbytes entry in
# docs/architecture/roadmap-next-steps.md), that is ~690KB -- under
# 0.1% of the current slack, nowhere near enough to threaten the
# 1536MiB limit.
_MAX_POLL_BATCH_SIZE_OVERRIDES: dict[str, int] = {
    "products": 100,
    "inventories": 100,
}

# Raised from 30.0 (2026-08-11): this pipeline has no real-time
# freshness requirement -- it's a portfolio/study project, streamed
# traffic only ever comes from a manually-run simulator
# (simulator_interval_seconds default 5s), and nothing downstream
# consumes Bronze streaming data on a live SLA (Gold is built from the
# separate batch flow, not this table). A low-volume entity used to
# flush on this timeout well before filling _MAX_BATCH_SIZE, producing
# one tiny Delta commit (+ transaction log entry) roughly every 30s of
# real traffic regardless of how few records it held -- confirmed live
# via real _delta_log commit timestamps (e.g. `carriers`, one of the
# platform's smallest entities, flushing 15-90s apart). 300.0 (5
# minutes) cuts that to at most one flush per 5 minutes of low-traffic
# time -- roughly a 10x reduction in age-triggered commits -- without
# touching _MAX_BATCH_SIZE, so the _FLUSH_POOL_SIZE memory budget
# above (sized around a 100-record max per-flush footprint) is
# completely unaffected. See docs/architecture/roadmap-next-steps.md
# for the real object-count investigation this responds to.
_MAX_BATCH_AGE_SECONDS = 300.0

# How long a single consume_batch() call blocks waiting for at least
# one message before returning empty-handed. 1.0s was safe when every
# entity had real backlog (consume_batch() returns almost instantly
# once data is ready, regardless of this value -- the timeout only
# matters for a genuinely empty poll), but as entities drain to zero
# lag during the Frente 3 reprocess, more and more of them started
# hitting this full 1.0s wait every single round-robin pass, directly
# lengthening every round and starving still-backlogged entities
# (confirmed live: mean round duration measured at 9.09s in a 3-minute
# window vs a 4.71s lifetime average -- see
# docs/architecture/roadmap-next-steps.md). 0.25s cuts that wasted
# wait 4x without punishing entities with real backlog (their
# consume_batch() calls are unaffected either way) -- not lower:
# librdkafka still needs enough of a window for a live trickle event
# to actually arrive and be returned within the same call, and going
# much below ~0.2s starts trading "faster empty polls" for "genuinely
# fresh events routinely needing an extra round to be picked up"
# instead, which is not the problem being solved here.
_POLL_TIMEOUT_SECONDS = 0.25

# Once an entity's consume_batch() calls come back empty
# _IDLE_AFTER_EMPTY_POLLS times in a row, it's treated as caught up
# (not just a one-off timing blip -- a single empty poll is common and
# not itself a signal of anything) and deprioritized: polled only
# every _IDLE_POLL_EVERY_N_ROUNDS-th round instead of every round,
# freeing the rounds in between for entities still in real backlog.
# The moment an idle entity's poll turn does return a message, its
# empty-poll streak resets to 0 and it's back to full-frequency
# polling immediately -- this is a live, self-correcting
# classification (see _EntityBuffer.consecutive_empty_polls), not a
# static list. 3 is enough to rule out a single blip without being
# slow to react; 5 (poll 1 round in 5) is a starting point, not a
# formula result -- revisit either number if a future measurement
# shows it under- or over-correcting.
_IDLE_AFTER_EMPTY_POLLS = 3

_IDLE_POLL_EVERY_N_ROUNDS = 5

# Bounds how many entities can flush (write_deltalake() + commit())
# concurrently -- see run_bronze_consumer()'s in_flight tracking,
# which also caps concurrency at 1 flush per *entity* regardless of
# this pool size. Derived from real, live measurement, not a formula
# guess (see "Batch-poll (max_messages=25) validated" and the
# librdkafka prefetch-buffer entry that follows it in
# docs/architecture/roadmap-next-steps.md):
#   - idle-of-flush baseline RSS (Kafka prefetch buffers capped via
#     queued.max.messages.kbytes, no flush in progress): ~750MB
#   - per-flush retained-memory footprint, sampled clean post-Kafka-fix
#     (rss_before/after around write_deltalake()+commit(), 40 samples
#     across all 14 active entities): mostly <6MB, max observed 26.5MB
#   - conservative per-flush budget: 40MB (safety margin over that max)
#   - target ceiling even at full pool utilization: 1200MB, i.e. ~336MB
#     (~22%) of slack left under the container's 1536M limit for the
#     Kafka buffers' own natural fluctuation, GC, and unmeasured
#     variance
#   - (1200 - 750) / 40 = 11.25 concurrent flushes -- rounded down to
#     a rounder, more conservative number
_FLUSH_POOL_SIZE = 8

STREAMING_ENTITIES: tuple[str, ...] = (
    "carriers",
    "categories",
    "customer_addresses",
    "customers",
    "inventories",
    "inventory_movements",
    "order_items",
    "order_status_history",
    "orders",
    "payment_methods",
    "payments",
    "products",
    "reviews",
    "sellers",
    "shipments",
    "warehouses",
)
"""
Mirrors the Debezium connector's ``table.include.list``
(``infrastructure/docker/debezium/connectors/marketplace-postgres.json``),
minus ``refunds``: the ``refunds`` table is empty in Postgres today and
``snapshot.mode: initial`` only creates a topic once a table's first
change event fires, so there is no ``refunds`` topic yet to subscribe
to. Refunds is also explicitly a "Future modules" entity in
project-decisions.md.
"""


def topic_for(entity: str) -> str:
    return f"{_TOPIC_PREFIX}{entity}"


@dataclass(slots=True)
class _EntityBuffer:
    records: list[dict[str, Any]] = field(default_factory=list)

    opened_at: float | None = None

    # Idle-round-skip bookkeeping (see _IDLE_AFTER_EMPTY_POLLS /
    # _IDLE_POLL_EVERY_N_ROUNDS) -- unrelated to the buffered records
    # themselves, kept here anyway since it shares the same
    # one-per-entity lifetime and run_bronze_consumer already threads
    # a `buffers` dict through its loop for exactly this kind of
    # per-entity state.
    consecutive_empty_polls: int = 0

    rounds_since_last_poll: int = 0

    def add(self, record: dict[str, Any]) -> None:
        if self.opened_at is None:
            self.opened_at = time.monotonic()

        self.records.append(record)

    def is_due(self, now: float) -> bool:
        if not self.records:
            return False

        if len(self.records) >= _MAX_BATCH_SIZE:
            return True

        return (
            self.opened_at is not None
            and (now - self.opened_at) >= _MAX_BATCH_AGE_SECONDS
        )

    def clear(self) -> None:
        self.records = []
        self.opened_at = None


def run_bronze_consumer(
    provider: MessagingProvider,
    *,
    entities: Sequence[str] = STREAMING_ENTITIES,
    max_iterations: int | None = None,
) -> None:
    """
    Consumes every topic in ``entities`` in a round-robin poll loop,
    micro-batching each entity's records (``_MAX_BATCH_SIZE`` messages
    or ``_MAX_BATCH_AGE_SECONDS``, whichever comes first) before
    writing them to that entity's Bronze Delta table and committing
    the consumed offsets.

    Flushes (``_flush()`` -- ``write_deltalake()`` + ``commit()``) run
    on a ``_FLUSH_POOL_SIZE``-worker thread pool instead of inline, so
    a slow S3 write for one entity no longer blocks every other
    entity's round-robin turn behind it. ``in_flight`` caps this at
    *one* flush per *entity* at a time (independent of pool size) and
    is the reason it's safe for the entity's ``_EntityBuffer`` to be
    mutated (``buffer.add()``) from the main thread while a previous
    flush for that same entity is still running in a worker thread:
    an entity's buffer is only ever touched by the main loop when that
    entity has no flush in flight, and only ever read by the one
    worker thread flushing it -- never both at once. See
    "Batch-poll (max_messages=25) validated" and the librdkafka
    prefetch-buffer entry that follows it in
    docs/architecture/roadmap-next-steps.md for how ``_FLUSH_POOL_SIZE``
    was sized.

    Each round-robin turn is also where two throughput adjustments
    live (see their constants' own comments for the full rationale):
    an entity is polled with a larger ``max_messages`` cap if it has a
    ``_MAX_POLL_BATCH_SIZE_OVERRIDES`` entry, and an entity that has
    come back empty ``_IDLE_AFTER_EMPTY_POLLS`` times in a row is
    polled only every ``_IDLE_POLL_EVERY_N_ROUNDS``-th round instead of
    every round, until it produces a message again.

    ``max_iterations`` bounds the number of round-robin cycles across
    all topics -- ``None`` (the default) runs forever, which is what
    the production entrypoint (``scripts/run_bronze_consumer.py``)
    wants; tests pass a small integer instead so the loop terminates
    on its own. Any flush still in flight when the loop ends is
    drained (``ThreadPoolExecutor``'s own ``__exit__`` blocks until
    every submitted task completes) before this function returns, so
    callers -- tests included -- always see a fully flushed, quiescent
    state once it does.
    """

    # include_cdc_metadata=True: this is the streaming path -- the one
    # that actually needs `_cdc_ts_ms` for out-of-order CDC events (see
    # resolve_bronze_schema's docstring). The batch flow
    # (PostgresExtractionStage) calls resolve_bronze_schema without
    # this flag, deliberately keeping its schema unchanged.
    schemas = {
        entity: resolve_bronze_schema(entity, include_cdc_metadata=True)
        for entity in entities
    }

    buffers = {entity: _EntityBuffer() for entity in entities}

    in_flight: dict[str, Future[None]] = {}

    iterations = 0

    with ThreadPoolExecutor(max_workers=_FLUSH_POOL_SIZE) as executor:

        while max_iterations is None or iterations < max_iterations:

            with ROUND_DURATION.time():

                for entity in entities:
                    topic = topic_for(entity)

                    buffer = buffers[entity]

                    future = in_flight.get(entity)

                    if future is not None and not future.done():
                        # A flush for this entity is still running --
                        # skip its turn entirely this round (both
                        # consuming and re-checking is_due()) rather
                        # than mutate or re-flush a buffer a worker
                        # thread might still be reading. Its own
                        # Consumer keeps prefetching in the background
                        # regardless (see the librdkafka prefetch-
                        # buffer roadmap entry), so nothing is lost by
                        # waiting -- just deferred a round or two.
                        #
                        # time.sleep(0) explicitly yields the GIL:
                        # without it, a tight loop with nothing else to
                        # do (few entities, no real network I/O to
                        # naturally release the GIL) can spin through
                        # every remaining round faster than the worker
                        # thread ever gets scheduled to actually run --
                        # confirmed live, this made a single-entity
                        # retry test fail 100% of the time regardless
                        # of how many extra rounds its max_iterations
                        # budget gave it. Production's real
                        # consume_batch() network calls make this less
                        # likely to matter there, but it's not
                        # guaranteed there either -- explicit is safer
                        # than relying on incidental I/O.
                        time.sleep(0)

                        continue

                    if future is not None:
                        # _flush() catches and logs every write/commit
                        # failure internally and never raises, so
                        # .result() should always be a no-op here --
                        # calling it anyway surfaces a genuine bug in
                        # _flush() itself instead of silently
                        # swallowing it, the same way a fire-and-forget
                        # submit() never would.
                        future.result()

                        del in_flight[entity]

                    # Idle-round-skip (see _IDLE_AFTER_EMPTY_POLLS /
                    # _IDLE_POLL_EVERY_N_ROUNDS): an entity that has
                    # come back empty-handed enough times in a row only
                    # gets its actual consume_batch() call once every
                    # _IDLE_POLL_EVERY_N_ROUNDS rounds, freeing the
                    # rounds in between for entities still in real
                    # backlog. is_due() below still runs every round
                    # regardless -- only the poll itself is skipped, so
                    # a buffer with leftover records never waits longer
                    # than it otherwise would to flush on age.
                    idle = buffer.consecutive_empty_polls >= _IDLE_AFTER_EMPTY_POLLS

                    skip_poll_this_round = (
                        idle
                        and buffer.rounds_since_last_poll
                        < _IDLE_POLL_EVERY_N_ROUNDS - 1
                    )

                    if skip_poll_this_round:
                        buffer.rounds_since_last_poll += 1
                    else:
                        buffer.rounds_since_last_poll = 0

                        # Caps the batch at whatever room is actually
                        # left in this entity's buffer (so a single
                        # consume_batch() call can't overshoot
                        # _MAX_BATCH_SIZE) and at this entity's
                        # _MAX_POLL_BATCH_SIZE_OVERRIDES value if it has
                        # one, else the default _MAX_POLL_BATCH_SIZE
                        # (so it can't pull an OOM-sized burst in one
                        # call either -- see that constant's own
                        # comment). If the buffer is already full, skip
                        # polling this entity entirely -- is_due()
                        # below will flush it this same iteration,
                        # freeing capacity for the next one.
                        remaining = min(
                            _MAX_BATCH_SIZE - len(buffer.records),
                            _MAX_POLL_BATCH_SIZE_OVERRIDES.get(
                                entity, _MAX_POLL_BATCH_SIZE
                            ),
                        )

                        if remaining > 0:
                            messages = provider.consume_batch(
                                topic,
                                group_id=_CONSUMER_GROUP_ID,
                                max_messages=remaining,
                                timeout_seconds=_POLL_TIMEOUT_SECONDS,
                                auto_commit=False,
                            )

                            if messages:
                                buffer.consecutive_empty_polls = 0

                                for message in messages:
                                    _buffer_message(
                                        entity, topic, message.value, buffer
                                    )
                            else:
                                buffer.consecutive_empty_polls += 1

                    if buffer.is_due(time.monotonic()):
                        in_flight[entity] = executor.submit(
                            _flush,
                            provider,
                            entity=entity,
                            topic=topic,
                            buffer=buffer,
                            schema=schemas[entity],
                        )

            iterations += 1


def _buffer_message(
    entity: str,
    topic: str,
    value: bytes,
    buffer: _EntityBuffer,
) -> None:
    MESSAGES_CONSUMED.labels(entity=entity, topic=topic).inc()

    try:
        change = decode_debezium_message(value)
    except Exception:
        logger.exception(
            "Skipping malformed Debezium message on topic '%s'.", topic
        )
        return

    if change.record is not None:
        # _cdc_ts_ms: Debezium's payload.source.ts_ms (the Postgres WAL
        # commit time), not the business `updated_at` column, which is
        # proven unreliable for ordering (see the roadmap entry on the
        # duplicate-row bug this resolves) -- a copy, not a mutation of
        # change.record, since DebeziumChange doesn't own the dict's
        # further lifecycle once returned.
        record = dict(change.record)
        record["_cdc_ts_ms"] = change.source_ts_ms

        buffer.add(record)


def _flush(
    provider: MessagingProvider,
    *,
    entity: str,
    topic: str,
    buffer: _EntityBuffer,
    schema: pa.Schema,
) -> None:
    try:
        table = pa.Table.from_pylist(
            [coerce_record(record, schema) for record in buffer.records],
            schema=schema,
        )

        with WRITE_DURATION.labels(entity=entity).time():
            write_deltalake(StorageConfig.bronze(entity), table, mode="append")

        # In-scope with the write on purpose: a commit failure (e.g.
        # KafkaException from a lost partition assignment, a
        # heartbeat/session timeout, or an unreachable broker -- all
        # observed live, see docs/architecture/roadmap-next-steps.md)
        # used to propagate uncaught out of run_bronze_consumer() and
        # kill the process. Handling it the same way as a write
        # failure -- log, leave the buffer intact, retry next cycle --
        # is deliberate: the buffer isn't cleared below, so the next
        # is_due() flush retries write_deltalake() *and* commit()
        # against the same records. If only the commit had failed
        # (the write already landed), that retry re-appends the same
        # rows -- an accepted duplicate, per this module's docstring
        # ("Bronze keeps every version of a row it has ever seen").
        provider.commit(topic, group_id=_CONSUMER_GROUP_ID)
    except Exception as exc:
        WRITE_FAILURES.labels(entity=entity).inc()

        # recover_from_lost_assignment() is a no-op (returns False) for
        # every failure except the provider's specific unrecoverable
        # group-membership-loss condition (Kafka: _ASSIGNMENT_LOST) --
        # see that method's docstring. The plain "leave the buffer
        # intact, retry next cycle" path above is correct and
        # self-healing for an ordinary transient failure, but not for
        # this one: the round-robin loop only calls consume_batch()
        # (the sole thing that lets the underlying client actually
        # process a revoked-and-rejoin membership change) when this
        # entity's buffer has room, and a commit failure never clears
        # it -- so once the buffer is exactly full when
        # _ASSIGNMENT_LOST hits, that gate stays shut forever and this
        # exact commit() keeps failing the exact same way, indefinitely
        # (confirmed live during the Frente 3 reprocess, see
        # docs/architecture/roadmap-next-steps.md, "commit-failure
        # retry can livelock an entity permanently"). Clearing the
        # buffer here is what breaks that deadlock: an empty buffer
        # reopens the round-robin's `remaining > 0` gate next round, so
        # consume_batch() runs again, which is what actually drives the
        # freshly recreated consumer through a real rejoin. The
        # records already written above (write_deltalake() succeeded;
        # only commit() failed) get re-fetched and re-appended once the
        # rejoined consumer resumes from the last *committed* offset --
        # the same accepted-duplicate tradeoff this module's docstring
        # already names for a bare commit failure, just now guaranteed
        # to resolve in one extra write instead of never resolving.
        if provider.recover_from_lost_assignment(
            topic, group_id=_CONSUMER_GROUP_ID, error=exc
        ):
            dropped = len(buffer.records)

            buffer.clear()

            logger.warning(
                "Bronze flush for entity '%s' lost its Kafka group "
                "assignment -- recreated the consumer and dropped the "
                "buffered batch (%d records, already durably written) "
                "so consumption can resume; the same records will be "
                "re-fetched and re-written once the consumer rejoins.",
                entity,
                dropped,
            )
        else:
            logger.exception(
                "Bronze flush failed for entity '%s' (%d buffered "
                "records) -- offsets left uncommitted, will retry next "
                "cycle.",
                entity,
                len(buffer.records),
            )

        return

    RECORDS_WRITTEN.labels(entity=entity).inc(len(table))

    lag = provider.consumer_lag(topic, group_id=_CONSUMER_GROUP_ID)

    if lag is not None:
        CONSUMER_LAG.labels(entity=entity, topic=topic).set(lag)

    buffer.clear()

    logger.info(
        "Wrote %d record(s) to Bronze for entity '%s'.",
        len(table),
        entity,
    )
