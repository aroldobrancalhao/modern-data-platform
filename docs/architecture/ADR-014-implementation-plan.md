# ADR-014 — Implementation Plan

Companion to `ADR-014-messaging-capabilities-event-stream-work-queue-and-ingestion-modes.md`.
This plan implements **Option A** (two capabilities), confirmed by the
author.

Rules that apply to every step:

- Nothing is implemented until the ADR and this plan are approved.
  After that, each step starts only on its own go-ahead.
- **Step 1 touches essential infrastructure** (`bronze-consumer` and
  its commit/livelock fix). Its plan and diff MUST be shown, and
  explicit approval received, before anything is applied.
- Unit tests run only in the scope listed per step: `tests/unit/streaming/`,
  the two messaging unit files approved for step 1, and the new test
  files each step creates. Never the full suite.
- Anything that needs containers (Kafka, NATS, RabbitMQ, Airflow, S3)
  is listed under "Deferred until memory allows" and is not run until
  the WSL host has memory to spare.
- Line references are as of 2026-10-11 and must be re-checked when
  each step starts.

---

# Step 1 — Align the event-stream contract without breaking Kafka

**Essential infrastructure. Explicit approval required before applying.**

Goal: make the existing contract honestly an *event stream* contract,
with no Kafka vocabulary in `data_platform`, and **zero behaviour
change**. Renames and docstrings only. Kafka's commit/recover logic is
moved verbatim, not rewritten.

## Changes

| File | Change |
|---|---|
| `src/data_platform/messaging/messaging_provider.py` → `event_stream_provider.py` | `class MessagingProvider` → `class EventStreamProvider`. `recover_from_lost_assignment` → `recover_consumer`. Neutral docstrings for `commit` (cumulative position, documented as log semantics), `recover_consumer` and `consumer_lag`. Kafka-specific text (`_ASSIGNMENT_LOST`, `CommitTimeoutError`) removed from here. Class docstring cites ADR-014 instead of ADR-0008 for retry/DLQ. |
| `src/data_platform/messaging/models.py` | `Message` gains `message_id: str \| None = None` as the **last** field, so existing positional and keyword construction stays valid. Docstring notes that `partition`/`offset` are event-stream only. |
| `src/data_platform/messaging/__init__.py` | Export `EventStreamProvider` (in place of `MessagingProvider`). |
| `src/integrations/kafka/messaging/kafka_messaging_provider.py` | Base class → `EventStreamProvider`. Method `recover_from_lost_assignment` → `recover_consumer`, **body unchanged** (`:190-233`). The Kafka-specific explanation moves from the contract's docstring into this method's docstring. |
| `src/streaming/consumers/bronze_consumer.py` | Import and type hints → `EventStreamProvider` (`:48`, `:325`, `:553`). Call site `:612` → `provider.recover_consumer(...)`. Comments mentioning `recover_from_lost_assignment` updated. No logic change. |
| `scripts/run_bronze_consumer.py` | Import and `cast` → `EventStreamProvider` (`:39`, `:68-70`). |
| `src/data_platform/processing/context_writers/messaging_context_writer.py` | Sets `MessagingKeys.MESSAGE_ID` when `message.message_id is not None`. Docstring updated: Kafka messages still leave it unset. |
| `tests/unit/streaming/consumers/test_bronze_consumer.py` | `FakeMessagingProvider(MessagingProvider)` → `FakeEventStreamProvider(EventStreamProvider)`, `recover_from_lost_assignment` → `recover_consumer`. The fake keeps mirroring the Kafka classification (`:157`), since it models the Kafka provider's behaviour for the bronze tests. |
| `tests/unit/integrations/kafka/messaging/test_kafka_messaging_provider.py` | Calls renamed to `recover_consumer`. Assertions unchanged. |
| `tests/unit/processing/context_writers/test_messaging_context_writer.py` | `test_write_never_sets_message_id` (`:97-110`) is replaced by two tests: MESSAGE_ID is unset when `message_id is None`, and set when it is present. |
| `tests/integration/kafka/test_bronze_consumer_real_kafka.py`, `tests/integration/kafka/test_messaging_context_writer_real_kafka.py` | Import/type renames only (`:104`, `:32` and the hints). Not run (deferred). |

Unchanged on purpose: `KafkaMessagingProvider` class name, the
`"kafka"` registry key (`src/integrations/kafka/bootstrap.py`),
`settings.messaging_provider` (`src/data_platform/config/settings.py:30`),
the `topic`/`group_id` parameter names, and `consume`/`consume_batch`/
`commit`/`consumer_lag` names and signatures.

## Resulting signatures

```python
class EventStreamProvider(BaseProvider, ABC):
    def produce(self, topic: str, value: bytes, key: str | None = None,
                headers: dict[str, bytes] | None = None) -> None: ...
    def consume(self, topic: str, group_id: str, timeout_seconds: float = 1.0,
                auto_commit: bool = True) -> Message | None: ...
    def consume_batch(self, topic: str, group_id: str, max_messages: int,
                      timeout_seconds: float = 1.0,
                      auto_commit: bool = True) -> list[Message]: ...
    def commit(self, topic: str, group_id: str) -> None: ...
    def recover_consumer(self, topic: str, group_id: str,
                         error: Exception) -> bool: ...          # renamed
    def consumer_lag(self, topic: str, group_id: str) -> int | None: ...
```

## Unit tests in scope

```bash
uv run pytest -q tests/unit/streaming/ \
  tests/unit/integrations/kafka/messaging/test_kafka_messaging_provider.py \
  tests/unit/processing/context_writers/test_messaging_context_writer.py
uv run ruff check <changed files>
```

## Acceptance criteria

- All tests above pass, with the same test count as before plus the
  one extra MESSAGE_ID test.
- `grep -rn "_ASSIGNMENT_LOST\|KafkaException\|recover_from_lost_assignment" src/data_platform`
  returns nothing.
- `git diff` of `kafka_messaging_provider.py` shows only the base
  class, the method name and docstrings. The bodies of `commit` and
  the renamed method are byte-identical.
- `git diff` of `bronze_consumer.py` shows only renames (import, type
  hints, one call, comments).

## Deferred until memory allows

- `tests/integration/kafka/` against a real broker.
- Running `bronze-consumer` live for at least one full flush cycle,
  checking `mdp_bronze_records_written_total` increments and
  `mdp_bronze_write_failures_total` stays flat.

---

# Step 2 — Work-queue capability with a minimal NATS JetStream provider

NATS JetStream is chosen for its small memory footprint.

## Changes

| File | Change |
|---|---|
| `src/data_platform/messaging/work_queue_provider.py` (new) | `WorkQueueProvider` ABC (signatures below). |
| `src/data_platform/messaging/models.py` | New `Delivery` dataclass. |
| `src/data_platform/messaging/__init__.py` | Export `WorkQueueProvider`, `Delivery`. |
| `src/data_platform/config/settings.py` | `work_queue_provider: str = "nats"`, next to `messaging_provider` (`:30`). |
| `src/integrations/nats/__init__.py`, `core/nats_context.py`, `messaging/nats_work_queue_provider.py`, `messaging/nats_builder.py`, `bootstrap.py` (new) | Provider, connection context and builder, mirroring `integrations/kafka/`'s layout. `bootstrap.register` adds the `"nats"` key. |
| `src/data_platform/bootstrap.py` | `register_nats(registry)` next to `register_kafka` (`:8`, `:20`). |
| `pyproject.toml`, `uv.lock` | Add `nats-py`. |
| `infrastructure/docker/docker-compose.yml` | `nats` service (JetStream enabled, small `mem_limit`, a volume for JetStream storage). Added but **not started** in this step. |
| `infrastructure/docker/.env` vs root `.env` | `NATS_URL` for the app goes in the root `.env`. Compose-only values go in `infrastructure/docker/.env`. These are two different files. |
| `tests/unit/messaging/fake_work_queue_provider.py` (new) | `FakeWorkQueueProvider`: in-memory queue with attempts, `max_attempts`, dead-letter list and `message_id` dedup. |
| `tests/unit/messaging/test_work_queue_contract.py` (new) | Contract tests written once against `WorkQueueProvider`. Parametrized over the fake now, and reused by the real providers later. |
| `tests/unit/integrations/nats/test_nats_work_queue_provider.py` (new) | Mocked JetStream client: translation to `Delivery`, ack/nak/term calls, DLQ republish when `attempt >= max_attempts`, `Nats-Msg-Id` header set from `message_id`. |

## Signatures

```python
@dataclass(frozen=True, slots=True)
class Delivery:
    message: Message          # message.message_id is always set here
    delivery_id: str          # provider handle used to ack/nack
    attempt: int              # 1 on first delivery


class WorkQueueProvider(BaseProvider, ABC):
    def publish(self, queue: str, value: bytes, *, message_id: str,
                headers: dict[str, bytes] | None = None) -> None: ...
    def receive(self, queue: str, consumer: str, max_messages: int,
                timeout_seconds: float = 1.0) -> list[Delivery]: ...
    def ack(self, delivery: Delivery) -> None: ...
    def nack(self, delivery: Delivery, *,
             delay_seconds: float | None = None) -> None: ...
    def dead_letter(self, delivery: Delivery, *, reason: str) -> None: ...
    def extend(self, delivery: Delivery, seconds: float) -> None: ...
    def depth(self, queue: str, consumer: str) -> int | None: ...
```

`max_attempts` and the dead-letter destination are provider
configuration, not per-call arguments.

Design point to settle while implementing: `nats-py` is asyncio-only,
while the platform contracts are synchronous (`bronze-consumer` is a
synchronous loop). The provider runs its own event loop on a
background thread and bridges each call with
`asyncio.run_coroutine_threadsafe`. That bridge gets its own unit
tests.

## Unit tests in scope

```bash
uv run pytest -q tests/unit/messaging/ tests/unit/integrations/nats/
uv run ruff check <changed files>
```

## Acceptance criteria

- The contract tests pass against `FakeWorkQueueProvider`: publish →
  receive → ack removes the message; nack redelivers with
  `attempt + 1`; exhausting `max_attempts` dead-letters; an explicit
  `dead_letter` is terminal; a duplicate `message_id` is not enqueued
  twice.
- The NATS provider unit tests pass with a mocked client.
- No `nats` import outside `src/integrations/nats/`.

## Deferred until memory allows

- `tests/integration/nats/` (new): the same contract test module
  parametrized over a real `NatsWorkQueueProvider` against the
  `nats` container.
- `docker stats` on the `nats` container under a small load,
  recording the real memory figure in the roadmap.

---

# Step 3 — Event-driven mode end to end

Goal: file landed → claim-check message → consumer → idempotent
ingestion. Then replace the metric-based watcher.

## 3a — File events

| File | Change |
|---|---|
| `src/data_platform/messaging/file_event.py` (new) | `FileEvent` dataclass plus `to_json`/`from_json`, validating the ADR-014 format (`schema_version` checked, required fields enforced). |
| `src/data_platform/ingestion_ledger/` (new; exact module name decided at step start) | `IngestionLedger` ABC: `claim(key, lease_seconds) -> ClaimResult`, `mark_succeeded(key, run_id)`, `mark_failed(key, reason)`, `get(key)`. Plus an in-memory fake for unit tests. |
| `src/integrations/postgres/...` (new module) | Postgres implementation of the ledger. Insert-if-absent claim, lease-based reclaim of stale `processing`. Instance and schema are open point 4 of ADR-014. |
| `scripts/emit_file_event.py` (new) | Local emitter: uploads a file through `StorageProvider.upload`, computes SHA-256, publishes a `FileEvent` through `WorkQueueProvider`. The cloud bridge (S3 → SQS/EventBridge → work queue) is open point 2 of ADR-014 and is not part of this step. |
| `src/streaming/consumers/file_event_consumer.py` (new) | Loop: `receive` → `FileEvent.from_json` (malformed → `dead_letter`) → `ledger.claim` (already succeeded → `ack` and skip) → `WorkflowProvider.trigger(workflow_id, parameters={uri, dataset, checksum, idempotency_key})` → record the run id → `ack`. A trigger failure → `nack` with delay. |
| `scripts/run_file_event_consumer.py` (new) | Entrypoint, mirroring `scripts/run_bronze_consumer.py`. |
| `airflow/dags/file_ingestion_pipeline.py` (new) | `schedule=None`, receives the event parameters, ingests the file into Bronze and, as its last task, marks the ledger `succeeded` or `failed`. The file-reading stage is new work in the processing framework (ADR-009); its design is detailed at step start, after reading the stage contracts. |

Recommended ledger semantics: the consumer acks after a successful
*trigger*, and the DAG owns the terminal state. Retries of a failed
run belong to Airflow. A `processing` key whose lease expires without
a terminal state is reclaimable. Alternative to decide at step start:
the consumer waits for the run to finish, keeping the delivery alive
with `extend`. That is simpler to reason about, but holds a delivery
for the whole run.

## 3b — Replace `order_status_history_lag_watcher`

**Touches `bronze-consumer`. Explicit approval required, same as
step 1.**

| File | Change |
|---|---|
| `src/streaming/consumers/bronze_consumer.py` | After a successful flush (after `commit`, next to `RECORDS_WRITTEN.inc`, `:639`), publish a `bronze.batch_written` event (entity, record count, Delta table version) via an optional `WorkQueueProvider`. A publish failure is logged and counted, and MUST NOT fail the flush. |
| `src/streaming/consumers/file_event_consumer.py` (or a sibling consumer) | Handles `bronze.batch_written`, coalescing so that at most one `marketplace_batch_pipeline` run is pending per entity. Ledger key = entity + Delta version. |
| `airflow/dags/order_status_history_lag_watcher.py`, `scripts/check_lag_watcher_would_fire.sh` | Paused first, removed only after the replacement is validated live. |

## Signatures

```python
@dataclass(frozen=True, slots=True)
class FileEvent:
    schema_version: int
    event_id: str
    event_type: str
    idempotency_key: str
    dataset: str
    uri: str
    size_bytes: int
    checksum_algorithm: str
    checksum_value: str
    content_type: str
    created_at: datetime
    emitted_at: datetime
    version_id: str | None = None

def run_file_event_consumer(queue_provider: WorkQueueProvider,
                            workflow_provider: WorkflowProvider,
                            ledger: IngestionLedger, *,
                            queue: str, consumer: str,
                            max_iterations: int | None = None) -> None: ...
```

## Unit tests in scope

```bash
uv run pytest -q tests/unit/messaging/ tests/unit/streaming/
```

New files: `tests/unit/messaging/test_file_event.py` and
`tests/unit/streaming/consumers/test_file_event_consumer.py` (fake
queue + fake ledger + `MagicMock(spec=WorkflowProvider)`). For 3b,
the existing `tests/unit/streaming/consumers/test_bronze_consumer.py`
is extended.

## Acceptance criteria

- The same event delivered twice triggers exactly one workflow run.
- The same content under a different URI triggers no new run.
- A malformed event ends in the dead-letter destination without
  blocking later events.
- A trigger failure is retried up to `max_attempts`, then
  dead-lettered.
- 3b: a failing `bronze.batch_written` publish never fails a flush
  (existing bronze tests still pass, plus a new one for this case).

## Deferred until memory allows

- Real Postgres ledger tests (`tests/integration/postgres/`, new).
- End to end: `emit_file_event.py` → NATS → consumer → Airflow DAG run
  → Bronze table → ledger `succeeded`.
- 3b live: watcher paused, `bronze.batch_written` triggers exactly one
  batch run per real change, observed for a full cycle before the
  watcher is removed.

---

# Step 4 — Second work-queue provider (proof of agnosticism)

**Recommendation: RabbitMQ (quorum queue + dead-letter exchange).** It
runs locally in a container, so no cloud account or cost is involved.
Pub/Sub would need either a GCP project or the emulator, and the
emulator's support for dead-letter topics and exactly-once delivery
must be verified first.

## Changes

| File | Change |
|---|---|
| `src/integrations/rabbitmq/...` (new, same layout as `integrations/nats/`) | `RabbitMqWorkQueueProvider` (quorum queue, `x-delivery-limit`, DLX; delayed retry via DLX + TTL). |
| `src/data_platform/bootstrap.py` | `register_rabbitmq(registry)`. |
| `pyproject.toml`, `uv.lock` | RabbitMQ client library (chosen at step start). |
| `infrastructure/docker/docker-compose.yml` | `rabbitmq` service, not started by default. |
| `tests/unit/messaging/test_work_queue_contract.py` | Unchanged. It is only parametrized over the new provider in the integration variant. |
| `tests/unit/integrations/rabbitmq/test_rabbitmq_work_queue_provider.py` (new) | Mocked-channel unit tests, as for NATS. |

## Unit tests in scope

```bash
uv run pytest -q tests/unit/messaging/ tests/unit/integrations/rabbitmq/
```

## Acceptance criteria (the actual proof)

- `test_work_queue_contract.py` passes unchanged against both NATS
  and RabbitMQ (integration variant).
- `file_event_consumer` runs against RabbitMQ by changing only
  `work_queue_provider` in settings, with **zero code changes** in
  `src/streaming/` or `src/data_platform/`.

## Deferred until memory allows

- Every integration test in this step, plus the end-to-end run from
  step 3 repeated on RabbitMQ.
