# ADR-014 — Messaging Capabilities: Event Stream, Work Queue and Ingestion Modes

Status: Accepted

The requirements in this ADR (three ingestion modes, broker-agnostic
messaging) are decided. The *shape* of the messaging contract (see
"Contract shape" below) is **Decision: Option A (confirmed by the
author)**.

The step-by-step implementation plan lives in
`ADR-014-implementation-plan.md`, so the plan can change without
reopening this decision.

---

# Context

## The broker-agnostic premise is already on record

Broker-agnostic messaging has been a platform premise since the first
ADRs. It was never stated as a standalone decision, but it appears
consistently:

- `ADR-000-architecture-principles.md:58`: "Cloud services must be
  abstracted behind provider implementations."
- `ADR-000-architecture-principles.md:154,162`: "Messaging Provider"
  is one of the platform providers, and "This allows replacing cloud
  implementations without changing business logic."
- `ADR-001-platform-architecture.md:152-154`: "Current
  implementation: - Apache Kafka". Kafka is the *current*
  implementation, not the only one.
- `ADR-001-platform-architecture.md:400`: "Messaging services remain
  interchangeable."
- `ADR-001-platform-architecture.md:405-412`: business code depends on
  `MessagingProvider`; possible implementations are Kafka, Event Hubs
  and Pub/Sub.
- `ADR-002-platform-contracts.md:160`: "Messaging should remain
  independent from the selected provider."
- `ADR-002-platform-contracts.md:166-175`: expected operations
  `publish()`, `subscribe()`, `ack()`, `retry()`, `dead_letter()`.
- `ADR-003-cloud-strategy.md:90`: capability mapping row
  "Messaging | Kafka / MSK | Event Hubs (Kafka API) | Pub/Sub / Kafka".
- `ADR-003-cloud-strategy.md:220`: "Messaging services expose
  identical behavior through platform contracts."
- `ADR-003-cloud-strategy.md:229`: "Business services publish events
  without provider awareness."
- `ADR-003-cloud-strategy.md:332-337`: replacing a provider should not
  require changes to Airflow DAGs, Spark jobs, business logic or
  platform services.
- `ADR-010 — Capability-Based Shared Execution Context.md:1301-1321`:
  example messaging providers (Kafka, MSK, Redpanda, Pub/Sub, Event
  Hub). Every implementation publishes `MessagingKeys.*`, and "The
  runtime does not know whether events originate from Kafka or
  Pub/Sub."
- `README.md:83` ("Provider-based abstractions") and `README.md:333`
  (Messaging row: Kafka / MSK, Event Hubs, Pub/Sub).

## What none of them record

- **Why Kafka was chosen.** `project-decisions.md:85-87` only lists
  "## Streaming / Apache Kafka". `ADR-0008-batch-vs-streaming.md:60`
  assigns event streaming to Kafka without comparing it to anything.
  See "Why Kafka" below.
- **That the platform needs two different messaging semantics**, not
  one (see "Problem Statement").
- **An event-driven ingestion mode** where an event triggers a batch
  (see "Ingestion modes").

---

# Problem Statement

## 1. Two independent axes were treated as one

ADR-0008 frames the platform as "Batch vs. Streaming". That puts two
different questions on a single axis:

- **Trigger: what starts a processing run.** A schedule, a discrete
  event (a file landed, a status changed), or a continuous flow
  (CDC: Debezium → Kafka → `bronze-consumer`).
- **Volume: how much data one run processes.** One record at a time,
  a micro-batch, or a full batch.

"Event" is a kind of trigger, not a third volume. A file that lands
can trigger a full batch. Because ADR-0008 collapses both axes into
one, it has no place for "an event triggers a batch". It goes as far
as stating the opposite: "Event-Driven Processing is restricted to
Streaming. Batch remains DAG-oriented."
(`ADR-0008-batch-vs-streaming.md:295-297`).

## 2. The messaging contract mixes two messaging semantics

| | Event stream (log) | Work queue |
|---|---|---|
| Examples | Kafka, Redpanda, RabbitMQ Streams | NATS JetStream (work-queue consumers), RabbitMQ queues, Pub/Sub, SQS |
| Unit of progress | Consumer position (offset), cumulative | Per-message acknowledgement |
| Replay | Native: any reader can re-read history | Not the point; a message is done once acked |
| Ordering | Per partition | Usually not guaranteed |
| Failure handling | Do not advance the position; retry topics | Negative ack, redelivery with a limit, dead-letter |
| Typical use | Streaming, CDC, several readers of the same history | "A file landed, process it exactly once" |

ADR-002 promised work-queue operations (`ack`, `retry`,
`dead_letter`). ADR-0008 puts event-stream behaviour in the broker
("Consumer Groups, Replay, Offset management, Retry Topics, Dead
Letter Queue", `ADR-0008-batch-vs-streaming.md:64-70`) and retry in
the consumers ("Retry is managed by Kafka consumers.",
`ADR-0008-batch-vs-streaming.md:203`). The real contract (below)
follows ADR-0008 and explicitly drops retry/DLQ. **The two ADRs
describe different things and were never reconciled.**

## 3. Event-driven ingestion exists only as an improvised workaround

`airflow/dags/order_status_history_lag_watcher.py` triggers
`marketplace_batch_pipeline` from a Prometheus metric
(`mdp_bronze_records_written_total`, `_PROMQL_QUERY` at `:186`). It is
event → batch, built without a messaging capability: the "event" is
inferred from a monitoring signal, not delivered as a message.

That design is what made the 2026-08-14 incident possible
(`docs/architecture/roadmap-next-steps.md:3026`, "fired
`marketplace_batch_pipeline` 188 times in 30 minutes"). The detection
had no memory of what it had already fired on, i.e. no watermark
(DAG docstring, `order_status_history_lag_watcher.py:30-44`). The fix
added a value watermark (`:191-224`), but the watermark is still
derived from an in-memory counter that resets whenever
`bronze-consumer` restarts (`:195-201`). This ADR does not revisit
that incident. It is cited as motivation: event-driven ingestion
needs a real event, carrying the identity of the work, with
deduplication built in.

---

# Current State

Read directly from the code on 2026-10-11:

- **Contract**: `src/data_platform/messaging/messaging_provider.py:18`,
  `MessagingProvider(BaseProvider, ABC)`:
  - `produce(topic, value, key=None, headers=None)` (`:34`)
  - `consume(topic, group_id, timeout_seconds, auto_commit)` (`:47`)
  - `consume_batch(topic, group_id, max_messages, timeout_seconds, auto_commit)` (`:74`)
  - `commit(topic, group_id)` (`:102`): cumulative, "up to its current
    position"
  - `recover_from_lost_assignment(topic, group_id, error)` (`:121`):
    its docstring names Kafka's `_ASSIGNMENT_LOST` and
    `KafkaMessagingProvider.CommitTimeoutError`
  - `consumer_lag(topic, group_id)` (`:157`): defined as a per-partition
    sum of (latest offset - position)
  - No `ack`, `retry` or `dead_letter`. The class docstring (`:27-30`)
    defers retry/DLQ to the caller "per ADR-0008".
- **Model**: `src/data_platform/messaging/models.py`. `Message` carries
  `topic`, `key`, `value`, `partition` (`:46`), `offset` (`:48`) and
  `headers`. It has no message id.
- **Only real provider**:
  `src/integrations/kafka/messaging/kafka_messaging_provider.py:56`,
  `KafkaMessagingProvider` (confluent-kafka). It is registered as
  `"kafka"` in `src/integrations/kafka/bootstrap.py` and built by
  `scripts/run_bronze_consumer.py:70`.
- **Test double**: `FakeMessagingProvider` in
  `tests/unit/streaming/consumers/test_bronze_consumer.py:74`. Its
  `recover_from_lost_assignment` mirrors the Kafka error
  classification (`:157`).
- **Only consumer of the contract**:
  `src/streaming/consumers/bronze_consumer.py`. It calls
  `consume_batch(..., auto_commit=False)` (`:492-498`), `commit` in
  `_flush` (`:582`), `recover_from_lost_assignment` (`:612`, the
  commit/livelock fix) and `consumer_lag` (`:641`). It also imports
  `decode_debezium_message` from `integrations.kafka` (`:52`). Its
  docstring accepts "No Dead Letter Queue and no sophisticated retry"
  (`:17`).
- **Context keys**:
  `src/data_platform/processing/core/context_keys/messaging_keys.py`
  defines `MESSAGE_ID`, `KEY`, `TOPIC`, `PARTITION`, `OFFSET` and
  `CONSUMER_GROUP`. `MessagingContextWriter` never sets `MESSAGE_ID`
  ("Kafka has no broker-level message id concept",
  `messaging_context_writer.py:43`).

## Divergences from the ADRs

1. **`commit()` is cumulative by offset, but ADR-002 promised `ack()`**
   (`ADR-002:166-175`). Per-message ack is what Pub/Sub, NATS JetStream,
   RabbitMQ and SQS expose; a cumulative position is Kafka's model.
2. **No `retry()` or `dead_letter()`**, both promised by ADR-002. The
   contract's own docstring justifies dropping them with ADR-0008,
   which assigns retry to "Kafka consumers"
   (`ADR-0008-batch-vs-streaming.md:203`). ADR-002 and ADR-0008
   contradict each other, and nothing records which one wins.
3. **`recover_from_lost_assignment()` is Kafka-specific in name and
   documented semantics.** That conflicts with "identical behavior"
   (`ADR-003:220`) and "interchangeable" (`ADR-001:400`).
4. **`consumer_lag()` is defined as partition offsets.** Pub/Sub has
   no partitions or offsets, and NATS JetStream reports pending
   counts instead.
5. **ADR-010 itself bakes in Kafka vocabulary.** It requires every
   implementation to publish `PARTITION` and `OFFSET`
   (`ADR-010:1307-1318`), which Pub/Sub cannot provide, while the
   `MESSAGE_ID` key that work queues *do* provide is never set.

The violations hit **Google Pub/Sub, which ADR-001, ADR-002, ADR-003
and ADR-010 all name explicitly**, not just a hypothetical new broker.
Kafka-protocol brokers (Event Hubs via the Kafka API, Redpanda) fit
the current contract unchanged.

---

# Decision

## 1. The platform MUST support three ingestion modes

The trigger axis is separate from the volume axis:

| Mode | Trigger | Typical volume | Messaging semantics | Where it lives today |
|---|---|---|---|---|
| **Scheduled** | Time (Airflow schedule) | Batch | None | Airflow. `marketplace_batch_pipeline` currently has `schedule=None` (`airflow/dags/marketplace_batch_pipeline.py:44-53,112`; the 30-min schedule was reverted for cost) and runs manually or through the watcher. `bronze_streaming_maintenance` is truly scheduled (`timedelta(days=1)`, `:93`) but is maintenance, not ingestion. |
| **Event-driven** | A discrete event (a file landed, a status changed) | Batch or micro-batch, one unit of work per event | Work queue | Improvised only: `order_status_history_lag_watcher` (metric → `TriggerDagRunOperator`). No messaging involved. |
| **Continuous streaming** | A continuous change flow (CDC) | Record or micro-batch | Event stream | Debezium → Kafka → `bronze-consumer` (`bronze_consumer.py`). |

- Each mode MUST call the same business services (ADR-0008's
  "Business Services" principle is kept).
- The event-driven mode MUST NOT infer events from monitoring
  metrics. Events MUST be delivered through the work-queue capability
  and carry the identity of the work (see "Claim check").
- In the event-driven mode, the message *triggers* a batch and does
  not *orchestrate* it. When the unit of work is a batch pipeline,
  the consumer starts it through `WorkflowProvider.trigger(workflow_id,
  parameters)` (`src/data_platform/workflow/workflow_provider.py:37-41`),
  and Airflow stays the batch orchestrator. This is consistent with
  ADR-0008's "Why Kafka is not orchestrating Batch". The rejected
  alternative in ADR-0008's "Why Airflow is not waiting for Kafka
  events" (a broker coordinating steps *inside* a DAG) stays
  rejected.

This amends ADR-0008, which covered only the scheduled and continuous
modes.

## 2. Messaging MUST be broker-agnostic, per semantics

- Business code and platform services MUST depend only on platform
  messaging contracts. They MUST NOT depend on broker types, broker
  error classes or broker vocabulary.
- Broker-specific failure handling (such as Kafka's
  `_ASSIGNMENT_LOST` and `CommitTimeoutError` handling, including the
  commit/livelock fix) MUST stay inside the provider, behind a
  provider-neutral method.
- Each messaging semantics (event stream, work queue) MUST have at
  least one real provider. Agnosticism MUST be proven with a second
  real provider for the work queue (see the implementation plan,
  step 4).
- Target brokers for this layer: Kafka (current), NATS JetStream,
  RabbitMQ (classic/quorum queues and Streams), Google Pub/Sub, and
  Kafka-API-compatible brokers (Azure Event Hubs, Redpanda). See
  "Provider mapping".

## 3. Contract shape — Decision: Option A (confirmed by the author)

Two options were considered. **Option A was chosen.**

### Option A (recommended): two capabilities

**`EventStreamProvider`** (log): replaces today's `MessagingProvider`.
It keeps everything that is genuinely log semantics. Parameter names
stay as they are today (`topic`, `group_id`) to keep the change to
`bronze-consumer` minimal:

- `produce(topic, value, key=None, headers=None)`
- `consume` / `consume_batch(topic, group_id, ..., auto_commit)`:
  read from the group's current position
- `commit(topic, group_id)`: cumulative, advances the group's
  position. This is correct log semantics, not a defect.
- `recover_consumer(topic, group_id, error) -> bool`: the provider-
  neutral form of `recover_from_lost_assignment`. It means "the
  provider recognized an unrecoverable consumer state and replaced
  the consumer". The Kafka-specific detail moves into
  `KafkaMessagingProvider`'s docstring.
- `consumer_lag(topic, group_id) -> int | None` (name kept, definition
  made neutral): messages available to the group that it has not yet
  committed. Each provider computes it in its own way (sum of
  partition offsets for Kafka, `num_pending` for JetStream).
- Replay (`seek` to a position or timestamp) is a contract
  requirement, but it is **not implemented until a real caller needs
  it**, since none exists today.

**`WorkQueueProvider`** (work queue), new:

- `publish(queue, value, *, message_id, headers=None)`: `message_id`
  is mandatory and doubles as the broker-side deduplication key when
  the broker supports one.
- `receive(queue, consumer, max_messages, timeout_seconds) -> list[Delivery]`:
  `Delivery` wraps `Message` with `delivery_id`, `message_id` and
  `attempt`.
- `ack(delivery)`: per message.
- `nack(delivery, *, delay_seconds=None)`: redelivery (retry). The
  provider enforces a configured `max_attempts`.
- `dead_letter(delivery, *, reason)`: an explicit, terminal move to
  the dead-letter destination. Exhausting `max_attempts` MUST also end
  in the dead-letter destination, whether through the broker's native
  mechanism or through the provider when the broker has none.
- `extend(delivery, seconds)`: keeps a long-running delivery from
  being redelivered (JetStream `in_progress`, Pub/Sub
  `modifyAckDeadline`, SQS `ChangeMessageVisibility`).
- `depth(queue, consumer) -> int | None`: backlog.

`Message` is shared. `partition` and `offset` stay optional and are
set only by event-stream providers. A `message_id` is added and set by
work-queue providers. `MessagingKeys.MESSAGE_ID` is then populated for
work queues, and `PARTITION`/`OFFSET` for streams. This amends ADR-010
(`:1307-1318`).

- **Pros**: each contract is honest about its semantics. No provider
  has to fake a concept it lacks (no fake offsets in Pub/Sub, no
  emulated per-message ack over Kafka offsets). The event-stream side
  is almost the current contract, so `bronze-consumer` changes are
  mostly renames. ADR-002's `ack`/`retry`/`dead_letter` finally have
  a home.
- **Cons**: two contracts, two fakes and two sets of context keys to
  maintain. A broker that can serve both (NATS JetStream, RabbitMQ)
  needs two provider classes, even if they share a connection or
  context. Callers must pick the right capability.

### Option B: a single contract with a generic ack

One `MessagingProvider` with `publish`, `receive -> list[Delivery]`,
`ack(delivery)`, `nack`, `dead_letter` and `lag`. Kafka emulates
per-message ack by tracking the highest contiguous acked offset per
partition and committing that. Retry/DLQ on Kafka is implemented with
retry/dead-letter topics.

- **Pros**: one contract, literally matching ADR-002. One fake. One
  mental model for callers.
- **Cons**: lowest common denominator. Replay and position have no
  place in the contract, so streaming callers lose them or they leak
  back in as optional methods. Kafka needs non-trivial new code
  (contiguous-offset tracking, retry topics) on the hottest path of
  the platform. `bronze-consumer` and its commit/livelock fix would
  have to be rewritten against ack semantics rather than renamed.
  Work-queue brokers still cannot honour position-based lag.

## 4. Claim check for file events

A message announcing a file MUST carry a **pointer** to the file,
never its content. Files can be large, and brokers have small message
limits. The storage layer stays the system of record.

Minimum file-event message (JSON, UTF-8):

```json
{
  "schema_version": 1,
  "event_id": "0b6f3c1e-6f0a-4c51-9a0e-3f1f6c2d9a77",
  "event_type": "file.created",
  "idempotency_key": "orders:sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
  "dataset": "orders",
  "object": {
    "uri": "s3://<bucket>/landing/orders/2026/10/11/orders_0001.csv",
    "size_bytes": 1048576,
    "checksum": { "algorithm": "sha256", "value": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08" },
    "content_type": "text/csv",
    "version_id": null,
    "created_at": "2026-10-11T14:03:22Z"
  },
  "emitted_at": "2026-10-11T14:03:23Z"
}
```

| Field | Required | Purpose |
|---|---|---|
| `schema_version` | yes | Evolve the format without breaking consumers |
| `event_id` | yes | Unique per emitted event; used as `message_id` for broker-side dedup |
| `event_type` | yes | `file.created` initially (`bronze.batch_written` follows; see "Open points", item 6) |
| `idempotency_key` | yes | Identity of the *work*: `<dataset>:<algorithm>:<checksum>` |
| `dataset` | yes | Target entity, so routing does not depend on parsing the path |
| `object.uri` | yes | The claim check itself |
| `object.size_bytes` | yes | Sanity check before and after download |
| `object.checksum` | yes | Integrity check and the dedup key |
| `object.content_type` | yes | Picks the reader (CSV, JSON, Parquet, ...) |
| `object.version_id` | no | Pins the exact object version when the storage is versioned |
| `object.created_at` | yes | When the object was created in storage |
| `emitted_at` | yes | When the event was emitted; used for latency metrics |

Open point: S3 event notifications do not carry a SHA-256 checksum.
The checksum must either be provided by the uploader (S3 additional
checksums) or computed by an enrichment step before the event is
published. See "Open points".

## 5. Idempotency and deduplication

Work-queue delivery is **at least once** on every target broker, so
duplicates MUST be expected and absorbed by the consumer:

1. **Broker-side dedup (best effort)**: `event_id` is passed as
   `message_id`. NATS JetStream deduplicates on `Nats-Msg-Id` within
   the stream's duplicate window, and Pub/Sub offers exactly-once
   delivery on subscriptions. RabbitMQ and SQS standard queues offer
   no equivalent. The platform MUST NOT rely on this layer.
2. **Consumer-side ledger (mandatory)**: a durable ingestion ledger
   keyed by `idempotency_key`, with states `received → processing →
   succeeded | failed | dead_lettered`. The consumer claims the key
   atomically (insert-if-absent) *before* starting the work. It acks
   the delivery only after the ledger records a terminal state. If the
   key is already `succeeded`, it acks and skips. If the key is
   `processing` with a stale lease, the work is reclaimed.
3. **Content, not location**: keying on the checksum means re-uploading
   identical content under a new name is a no-op, while a corrected
   file with the same name is new work.

These are the watcher lessons turned into rules, without rewriting
that history (`roadmap-next-steps.md:3026`). The original watcher
had no memory of what it had fired on. Its current watermark lives in
an Airflow Variable derived from an in-memory counter that resets when
`bronze-consumer` restarts (`order_status_history_lag_watcher.py:195-201`).
Dedup state therefore MUST be:

- keyed by the identity of the unit of work, not by an aggregate
  signal;
- durable and independent of any producer's process lifetime;
- recorded *before* the heavy work is triggered. The watcher already
  does this part correctly: `Variable.set` runs before the trigger,
  at `:223`.

---

# Provider Mapping

Capabilities: **ES** = `EventStreamProvider`, **WQ** =
`WorkQueueProvider`. Broker behaviour below reflects general knowledge
of each broker and MUST be re-verified against current documentation
when each provider is implemented.

| Broker | ES | WQ | What fits unchanged | What needs adaptation |
|---|---|---|---|---|
| **Apache Kafka** (current) | Native | Not targeted | The whole current contract | WQ would need retry/DLQ topics and per-message ack emulation (Kafka "share groups", KIP-932, are newer; maturity to verify). Not planned. |
| **Azure Event Hubs (Kafka API)** | Via the Kafka provider | No | `KafkaMessagingProvider` as is | Configuration only (endpoint, SASL/OAuth). Tier limits on partitions and consumer groups need verifying. |
| **Redpanda** | Via the Kafka provider | No | `KafkaMessagingProvider` as is | Configuration only |
| **NATS JetStream** | Adaptation | Native | WQ: durable pull consumer, explicit ack, `nak` with delay, `max_deliver`, backoff, `in_progress`, `Nats-Msg-Id` dedup | WQ: no native dead-letter queue; the provider republishes to a DLQ subject on `term` or when attempts are exhausted (JetStream emits a max-deliveries advisory). ES: offset = stream sequence, `partition = None`, `commit` = ack-all, `lag` = `num_pending`, `recover_consumer` normally a no-op. |
| **RabbitMQ: classic/quorum queues** | No | Native | `ack`, `nack`/requeue, dead-letter exchange; delivery limit on quorum queues | Delayed retry needs the DLX + TTL pattern or a plugin. Quorum queues are preferred for redelivery limits. |
| **RabbitMQ Streams** | Adaptation | No | Append-only log, offsets, replay by offset or timestamp, server-side offset tracking | Different client library and protocol. Super streams for partitioning. `commit` = store offset. |
| **Google Pub/Sub** | Adaptation (not recommended) | Native | `ack`, `modifyAckDeadline`, dead-letter topic with max delivery attempts, retry policy, exactly-once option | ES: no partitions or offsets (`None`), replay via seek to snapshot or timestamp, lag only via Cloud Monitoring. |
| **Amazon SQS** (reference, not a target) | No | Native | Visibility timeout, `ChangeMessageVisibility`, redrive policy (DLQ + `maxReceiveCount`) | Listed because S3 event notifications target SQS natively. It is the likely *event source* on AWS (see "Open points"). |

---

# Why Kafka

> **PLACEHOLDER — retrospective record, to be completed by the
> author.** No motivations are invented here.
>
> - Reasons Kafka was chosen: _(author)_
> - Constraints at the time (CDC with Debezium, market demand,
>   portfolio goals, ...): _(author)_
> - Trade-offs accepted: _(author)_

Alternatives **not formally evaluated at the time** (no record found
in `docs/` or the README): NATS JetStream, RabbitMQ, Apache Pulsar,
Redpanda, Amazon Kinesis, Amazon SQS, Google Pub/Sub, Azure Event
Hubs. Several of these appear in earlier ADRs only as *possible
implementations*, never as evaluated alternatives.

---

# Alternatives Considered

## Keep a single contract and add `ack`/`retry`/`dead_letter` to it

Rejected. This is Option B above; see its cons there. Option A was
confirmed by the author.

## Event-driven mode via Airflow 3 event-driven scheduling (asset watchers)

The project runs Airflow 3.3.0 (`infrastructure/docker/airflow/Dockerfile:1`),
which can schedule DAGs from message-queue triggers. That would put
the queue client inside Airflow and bypass the platform messaging
contract, violating the agnostic premise for this capability. The
idempotency ledger would still be required. Not adopted as the
primary path. It can be revisited as an *implementation* of the
consumer side if it can sit behind `WorkQueueProvider`.

## Keep the metric-based watcher and harden it further

Rejected. A metric cannot carry the identity of the unit of work,
which is the root of the dedup problem described above.

---

# Consequences

## Positive

- The agnostic premise of ADR-000/001/002/003/010 becomes testable:
  each capability has an explicit contract and a fake, and step 4 of
  the plan proves the work queue with a second broker.
- The ADR-002 vs. ADR-0008 contradiction is resolved: `ack`, `retry`
  and `dead_letter` belong to the work queue, and position/replay
  belong to the event stream.
- On-demand file ingestion gets a real design (claim check + ledger)
  instead of a metric-driven workaround.

## Negative / risks

- **Any change to the event-stream contract touches `bronze-consumer`
  and its commit/livelock fix** (`bronze_consumer.py:582,612`;
  `kafka_messaging_provider.py:140-233`). This is essential
  infrastructure. Step 1 of the plan requires explicit approval and
  MUST be behaviour-preserving.
- **CDC stays tied to Kafka.** Debezium runs as a Kafka Connect
  connector (`infrastructure/docker/docker-compose.yml:551`,
  `debezium-connect`). Moving CDC to NATS would require Debezium
  Server with its NATS JetStream sink, a different deployment. Out of
  scope. CDC remains the event-stream capability's Kafka use case.
- `decode_debezium_message` lives under `integrations/kafka/` but is
  imported by `streaming/consumers/bronze_consumer.py:52`. The
  Debezium envelope is a CDC format, not a Kafka one. Moving it is
  optional cleanup, not required by this ADR.
- More moving parts locally. NATS JetStream is chosen for step 2
  partly for its small memory footprint, but every new container
  competes with Kafka (`mem_limit` 1024M,
  `docker-compose.yml:506`) and Kafka Connect (1024M, `:653`) on a
  memory-constrained WSL host.

## Open points

1. **Contract shape**: resolved, Option A (confirmed by the author).
   Kept in this list so the item numbers referenced elsewhere stay
   stable.
2. **File event source**: on AWS, S3 → SQS/EventBridge is native and
   S3 → NATS is not. Locally, a small emitter (upload helper or poller)
   would publish claim-check messages. The bridge from the cloud event
   source into the work-queue provider has to be decided in step 3.
3. **Checksum origin**: uploader-provided (S3 additional checksums)
   vs. computed by an enrichment step.
4. **Ledger location**: which Postgres instance and schema (for
   example a dedicated schema on an existing instance) and the lease
   duration for `processing`.
5. **Retry policy defaults**: `max_attempts`, backoff and dead-letter
   destination naming per broker.
6. **`order_status_history_lag_watcher` retirement**: the watcher
   reacts to new CDC data landing in Bronze, not to a file. Replacing
   it needs a second event type (`bronze.batch_written`, published by
   `bronze-consumer` after a successful flush) on the same work queue
   and ledger, with the idempotency key being entity + Delta table
   version. Because that touches `bronze-consumer` again, it needs the
   same explicit approval as step 1. The exact cut-over (pause, then
   remove) is decided in step 3.

---

# Related ADRs

- ADR-000 – Architecture Principles
- ADR-001 – Platform Architecture
- ADR-002 – Platform Contracts (messaging contract reconciled by this ADR)
- ADR-003 – Cloud Strategy
- ADR-0008 – Batch and Streaming Processing Architecture (amended: third ingestion mode, retry/DLQ placement)
- ADR-007 – Workflow Capability (`WorkflowProvider.trigger` used by the event-driven mode)
- ADR-010 – Capability-Based Shared Execution Context (`MessagingKeys` per capability)
