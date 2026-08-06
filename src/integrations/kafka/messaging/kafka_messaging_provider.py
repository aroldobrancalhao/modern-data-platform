from __future__ import annotations

from typing import cast

from confluent_kafka import Consumer
from confluent_kafka import Message as ConfluentMessage
from confluent_kafka import TopicPartition

from data_platform.messaging.messaging_provider import MessagingProvider
from data_platform.messaging.models import Message

from integrations.kafka.core.kafka_context import KafkaContext


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

        consumer.commit(asynchronous=False)

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
