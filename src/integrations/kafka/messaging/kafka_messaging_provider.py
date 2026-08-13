from __future__ import annotations

import threading
from typing import cast

from confluent_kafka import Consumer
from confluent_kafka import KafkaError
from confluent_kafka import KafkaException
from confluent_kafka import Message as ConfluentMessage
from confluent_kafka import TopicPartition

from data_platform.messaging.messaging_provider import MessagingProvider
from data_platform.messaging.models import Message

from integrations.kafka.core.kafka_context import KafkaContext

# Bounds commit()'s synchronous consumer.commit(asynchronous=False)
# call. confluent-kafka's Consumer.commit() takes no timeout
# parameter of its own -- KafkaContext.create_consumer() bounds a
# single broker round trip (socket.timeout.ms=30000) and how long a
# silent coordinator is tolerated before this consumer is evicted
# from the group (session.timeout.ms=45000, surfaced as
# KafkaError._ASSIGNMENT_LOST, already handled by
# recover_from_lost_assignment()), but neither bounds retries at the
# librdkafka client level -- a persistently unstable coordinator can
# still keep the call blocked past both. 60s leaves room for one full
# retried request-response cycle at socket.timeout.ms's 30s (30 + 30)
# before this blunter, client-side deadline fires, and is itself
# beyond session.timeout.ms's 45s so the more specific
# _ASSIGNMENT_LOST path gets a chance to fire first (see
# KafkaContext.create_consumer()'s own comments). This is the fix for
# docs/architecture/roadmap-next-steps.md's "Issue 2": a hung
# commit() with no bound anywhere silently stopped one entity's
# flushes for ~9h with no error, no crash, and no metric signal.
_COMMIT_TIMEOUT_SECONDS = 60


class CommitTimeoutError(Exception):
    """
    Raised by commit() when the underlying synchronous
    Consumer.commit(asynchronous=False) call does not return within
    _COMMIT_TIMEOUT_SECONDS.

    Past this deadline, whether the commit actually landed on the
    broker is unknown -- the call keeps running on a background
    thread (Python cannot forcibly stop a thread blocked inside
    librdkafka's C extension) and may still succeed, fail, or keep
    hanging at any point after this exception is raised. The only
    safe response is to stop trusting this Consumer instance rather
    than retry against it -- see recover_from_lost_assignment(),
    which treats this the same as KafkaError._ASSIGNMENT_LOST for
    exactly that reason.
    """


class KafkaMessagingProvider(MessagingProvider):
    """
    Apache Kafka implementation of MessagingProvider, backed by
    confluent-kafka.

    MessagingProvider already extends BaseProvider (see ADR-010), so
    this class inherits it transitively. Mixing BaseProvider in again
    here directly would make the MRO ambiguous -- BaseProvider would
    need to both precede and follow MessagingProvider at the same
    time -- and Python refuses to create such a class. This mirrors
    how AirflowWorkflowProvider(WorkflowProvider) and
    DatabricksComputeProvider(ComputeProvider) are defined.
    """

    def __init__(self, context: KafkaContext) -> None:
        self._context = context
        self._consumers: dict[tuple[str, str], Consumer] = {}

    def produce(
        self,
        topic: str,
        value: bytes,
        key: str | None = None,
        headers: dict[str, bytes] | None = None,
    ) -> None:

        producer = self._context.producer

        producer.produce(
            topic,
            value=value,
            key=key,
            headers=cast(
                "dict[str, str | bytes | None] | None",
                headers,
            ),
        )

        producer.flush()

    def consume(
        self,
        topic: str,
        group_id: str,
        timeout_seconds: float = 1.0,
        auto_commit: bool = True,
    ) -> Message | None:

        consumer = self._resolve_consumer(topic, group_id, auto_commit)

        record = consumer.poll(timeout_seconds)

        if record is None:
            return None

        if record.error():
            raise RuntimeError(str(record.error()))

        return self._to_message(record)

    def consume_batch(
        self,
        topic: str,
        group_id: str,
        max_messages: int,
        timeout_seconds: float = 1.0,
        auto_commit: bool = True,
    ) -> list[Message]:

        consumer = self._resolve_consumer(topic, group_id, auto_commit)

        records = consumer.consume(max_messages, timeout_seconds)

        messages: list[Message] = []

        for record in records:

            if record.error():
                raise RuntimeError(str(record.error()))

            messages.append(self._to_message(record))

        return messages

    def commit(
        self,
        topic: str,
        group_id: str,
    ) -> None:
        cache_key = (topic, group_id)

        consumer = self._consumers.get(cache_key)

        if consumer is None:
            raise RuntimeError(
                f"commit() called for ({topic!r}, {group_id!r}) before "
                "any consume() call resolved a consumer for that pair."
            )

        # consumer.commit(asynchronous=False) has no timeout parameter
        # of its own (see _COMMIT_TIMEOUT_SECONDS above), so the bound
        # is enforced here instead: run it on a background thread and
        # stop waiting after _COMMIT_TIMEOUT_SECONDS. daemon=True so
        # a thread that never returns can't block process exit; left
        # unjoined past the timeout deliberately -- joining further
        # would just reintroduce the same unbounded wait this exists
        # to remove. A second thread later calling close() on this
        # same Consumer while this one is still stuck inside it (the
        # CommitTimeoutError path below) is safe: librdkafka's
        # rd_kafka_t handles are documented safe for concurrent calls
        # from multiple threads, and any exception either call raises
        # as a result is already caught here or in
        # recover_from_lost_assignment()'s own close().
        commit_errors: list[Exception] = []

        def _commit() -> None:
            try:
                consumer.commit(asynchronous=False)
            except Exception as exc:  # noqa: BLE001 -- re-raised on the caller's thread below, not swallowed
                commit_errors.append(exc)

        commit_thread = threading.Thread(target=_commit, daemon=True)
        commit_thread.start()
        commit_thread.join(_COMMIT_TIMEOUT_SECONDS)

        if commit_thread.is_alive():
            raise CommitTimeoutError(
                f"commit() for ({topic!r}, {group_id!r}) did not "
                f"return within {_COMMIT_TIMEOUT_SECONDS}s."
            )

        if commit_errors:
            raise commit_errors[0]

    def recover_from_lost_assignment(
        self,
        topic: str,
        group_id: str,
        error: Exception,
    ) -> bool:
        is_assignment_lost = (
            isinstance(error, KafkaException)
            and error.args[0].code() == KafkaError._ASSIGNMENT_LOST
        )

        # CommitTimeoutError means commit()'s outcome is unknown and
        # may still be running on its own background thread (see that
        # class's docstring) -- just as unrecoverable by retrying
        # against the same Consumer as _ASSIGNMENT_LOST, since a
        # retried commit() would face the exact same risk of never
        # returning.
        if not (is_assignment_lost or isinstance(error, CommitTimeoutError)):
            return False

        cache_key = (topic, group_id)

        consumer = self._consumers.pop(cache_key, None)

        if consumer is not None:
            try:
                consumer.close()
            except Exception:
                # Best-effort only: for _ASSIGNMENT_LOST, the broker
                # already stopped considering this consumer a group
                # member, so a clean leave-group on close() isn't
                # guaranteed to succeed. For CommitTimeoutError, the
                # abandoned commit() thread may still be running
                # concurrently against this same Consumer -- close()
                # racing with it is expected, not a bug (see commit()'s
                # own comment on why that's safe). Either way, a clean
                # close() isn't required: discarding the reference
                # above (so the next _resolve_consumer() call builds a
                # fresh replacement) is what actually matters;
                # swallowing a close() failure here must not stop that
                # from happening.
                pass

        return True

    def consumer_lag(
        self,
        topic: str,
        group_id: str,
    ) -> int | None:
        consumer = self._consumers.get((topic, group_id))

        if consumer is None:
            return None

        assignment = consumer.assignment()

        if not assignment:
            return 0

        positions = consumer.position(assignment)

        lag = 0

        for partition in positions:
            # position() returns OFFSET_INVALID (-1001) for a
            # partition the consumer has never consumed from yet --
            # treat that as "as far behind as the broker's own low
            # watermark", not 0, so an idle-but-assigned partition
            # doesn't understate lag.
            #
            # cached=True: per get_watermark_offsets' own docstring,
            # the high offset (the side that matters -- lag is
            # high - position) is updated on every message fetched
            # for the partition, so it's effectively real-time for a
            # partition being actively polled, which is always true
            # here (this is only ever called right after a successful
            # flush, i.e. after consume() has been fetching from this
            # topic continuously). cached=False was measured at
            # 1.2-1.5s per call (3 partitions) in this project's own
            # environment -- a real, significant cost on the hot path
            # given this runs on every flush. The low offset's cache
            # only refreshes with statistics.interval.ms set, which
            # KafkaContext.create_consumer() now does.
            low, high = consumer.get_watermark_offsets(
                TopicPartition(partition.topic, partition.partition),
                cached=True,
            )

            current = partition.offset if partition.offset >= 0 else low

            lag += max(high - current, 0)

        return lag

    def _resolve_consumer(
        self,
        topic: str,
        group_id: str,
        auto_commit: bool = True,
    ) -> Consumer:
        """
        Reuses one Consumer per (topic, group_id) pair across calls.

        confluent-kafka's group-join/partition-assignment handshake is
        expensive, and consume() is meant to be called repeatedly (per
        the MessagingProvider contract) -- creating a new Consumer on
        every call would pay that cost every time, and could easily
        never return a message within timeout_seconds.

        ``auto_commit`` only has an effect the first time a given
        (topic, group_id) pair is resolved -- see consume()'s
        docstring.
        """

        cache_key = (topic, group_id)

        if cache_key not in self._consumers:
            consumer = self._context.create_consumer(
                group_id,
                enable_auto_commit=auto_commit,
            )
            consumer.subscribe([topic])
            self._consumers[cache_key] = consumer

        return self._consumers[cache_key]

    @staticmethod
    def _to_message(record: ConfluentMessage) -> Message:
        """
        Translates a confluent_kafka.Message into our provider-
        agnostic Message -- the confluent-kafka type never leaves
        this Provider.

        confluent-kafka types topic()/value() as Optional (the same
        Message class also represents errors/events), but a record
        that reaches this point already passed the record.error()
        check in consume(), so both are always present in practice --
        the RuntimeErrors below only guard against a contract change
        upstream, mirroring how DatabricksClient.run() guards
        completed_run.run_id.
        """

        topic = record.topic()

        if topic is None:
            raise RuntimeError(
                "Kafka returned a consumed record without a topic."
            )

        value = record.value()

        if value is None:
            raise RuntimeError(
                "Kafka returned a consumed record without a value."
            )

        key = record.key()

        raw_headers = record.headers() or []
        header_items = (
            raw_headers.items()
            if isinstance(raw_headers, dict)
            else raw_headers
        )

        return Message(
            topic=topic,
            key=key.decode("utf-8") if key is not None else None,
            value=value,
            partition=record.partition(),
            offset=record.offset(),
            headers={
                header_key: header_value
                for header_key, header_value in header_items
                if isinstance(header_value, bytes)
            },
        )
