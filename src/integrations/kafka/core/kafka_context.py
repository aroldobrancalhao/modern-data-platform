from __future__ import annotations

from functools import cached_property

from confluent_kafka import Consumer, Producer

from integrations.kafka.config.kafka_settings import KafkaSettings


class KafkaContext:
    """
    Shared Kafka context.

    Responsible for creating the confluent-kafka Producer/Consumer
    clients from KafkaSettings.
    """

    def __init__(
        self,
        settings: KafkaSettings | None = None,
    ) -> None:
        self._settings = settings or KafkaSettings()

    @property
    def settings(self) -> KafkaSettings:
        return self._settings

    @cached_property
    def producer(self) -> Producer:
        """
        A single Producer shared across every topic: unlike Consumer,
        a Producer is not scoped to any particular topic/partition or
        consumer group, so there is no reason to create more than one.
        """
        return Producer(
            {
                "bootstrap.servers": self._settings.bootstrap_servers,
            }
        )

    def create_consumer(
        self,
        group_id: str,
        enable_auto_commit: bool = True,
    ) -> Consumer:
        """
        Creates a new Consumer configured for the given consumer
        group.

        Unlike ``producer``, this is a factory method rather than a
        cached property: a Consumer is scoped to a single group.id
        (and, once subscribed, a set of topics), so the caller is
        responsible for keeping and reusing the returned instance
        across repeated polls instead of creating a new one every
        time.

        ``enable_auto_commit`` defaults to True (confluent-kafka's own
        default), matching every existing caller. Pass False for a
        consumer whose caller wants to commit offsets manually only
        after the consumed message has been durably processed (e.g.
        the Bronze Consumer -- see ADR-0008's streaming flow -- commits
        only after a micro-batch is written to Delta, for at-least-once
        delivery).
        """
        return Consumer(
            {
                "bootstrap.servers": self._settings.bootstrap_servers,
                "group.id": group_id,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": enable_auto_commit,
                # Without this, get_watermark_offsets(cached=True)'s
                # low-offset side never refreshes (per its own
                # docstring: "low offset is updated periodically if
                # statistics.interval.ms is set") -- the high offset
                # doesn't need it (updated on every fetched message),
                # but low is the fallback consumer_lag() uses for a
                # partition with no committed position yet. 30s to
                # match _MAX_BATCH_AGE_SECONDS
                # (streaming/consumers/bronze_consumer.py) -- no
                # per-call network cost, just periodic internal
                # bookkeeping.
                "statistics.interval.ms": 30000,
                # librdkafka's default (65536 KB = 64 MiB) applies per
                # partition, not per Consumer -- confirmed live via a
                # temporary stats_cb plus `kafka-topics --describe`
                # (every marketplace topic has 3 partitions), which
                # means the real per-Consumer ceiling was 3 x 64MiB =
                # 192MB, not 64MB. The Bronze Consumer holds 16
                # independent Consumer instances (one per entity, see
                # KafkaMessagingProvider._resolve_consumer), each
                # prefetching from a topic with a deep backlog --
                # measured live at ~1.5GB aggregate RSS, right at the
                # container's 1536M limit with no real headroom (see
                # "Bronze Consumer's ~1.5GB memory plateau..." in
                # docs/architecture/roadmap-next-steps.md). 16384 (16
                # MiB/partition x 3 partitions = 48MB/consumer, x 16
                # consumers = 768MB worst case) brings that down to a
                # range with real margin. Confirmed live afterward:
                # RSS dropped to ~755-865MB and per-topic throughput
                # actually improved (~1.8x) rather than regressing --
                # the smaller prefetch buffer never became the
                # bottleneck the pre-change analysis worried it might.
                "queued.max.messages.kbytes": 16384,
            }
        )
