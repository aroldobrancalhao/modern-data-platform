"""
Modern Data Platform
Processing Framework

Real-Kafka smoke test for the Messaging (Kafka) chain.

Proves the ADR-010 execution chain closes end to end against the
actual local Kafka broker (docker compose, mdp-kafka) and a real
KafkaMessagingProvider -- not a fake.

Reuses the `real_kafka` marker, excluded from the default suite. Run
it explicitly with:

    uv run pytest tests/integration/kafka/test_messaging_context_writer_real_kafka.py -m real_kafka -v

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from typing import cast

import pytest
from confluent_kafka.admin import AdminClient, NewTopic

from data_platform.bootstrap import bootstrap
from data_platform.config.settings import Settings
from data_platform.messaging.messaging_provider import MessagingProvider
from data_platform.processing.context_writers.messaging_context_writer import (
    MessagingContextWriter,
)
from data_platform.processing.core.context_keys.messaging_keys import (
    MessagingKeys,
)
from data_platform.processing.core.context_keys.processing_keys import (
    ProcessingKeys,
)
from data_platform.processing.core.execution_metadata import (
    ExecutionMetadata,
)
from data_platform.processing.core.execution_status import ExecutionStatus
from data_platform.processing.core.pipeline import Pipeline
from data_platform.processing.core.pipeline_result import PipelineResult
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)
from data_platform.processing.core.stage import Stage
from data_platform.processing.core.stage_result import StageResult
from data_platform.processing.executor.sequential_executor import (
    SequentialExecutor,
)
from data_platform.providers.provider_factory import ProviderFactory

pytestmark = [pytest.mark.anyio, pytest.mark.real_kafka]

BOOTSTRAP_SERVERS = "localhost:9092"

MESSAGE_VALUE = b"smoke-test-payload"
MESSAGE_KEY = "smoke-test-key"


@dataclass(eq=False, slots=True, kw_only=True)
class MessageConsumingStage(Stage):
    """
    Minimal concrete Stage used only to prove that a Message consumed
    from a real MessagingProvider (resolved through the Stage's
    ProviderFactory) is correctly published into the ProcessingContext
    by MessagingContextWriter.

    Polls in a short, bounded loop (up to ``max_attempts`` times, one
    second each) instead of a single poll: the message is produced
    before this Stage runs, but Kafka's consumer group join/partition-
    assignment handshake is asynchronous, so the first few polls can
    legitimately return None even though the message already sits on
    the broker.
    """

    provider_name: str

    topic: str

    group_id: str

    async def execute(
        self,
        context: ProcessingContext,
    ) -> StageResult:

        provider = self.resolve_provider(self.provider_name)
        assert isinstance(provider, MessagingProvider)

        message = None

        for _ in range(self.max_attempts):
            message = provider.consume(
                self.topic,
                group_id=self.group_id,
                timeout_seconds=1.0,
            )

            if message is not None:
                break

        if message is None:
            raise RuntimeError(
                f"No message consumed from topic '{self.topic}' "
                f"after {self.max_attempts} attempts."
            )

        MessagingContextWriter.write(
            message,
            context,
            group_id=self.group_id,
        )

        return StageResult(
            status=ExecutionStatus.COMPLETED,
            metadata=context.metadata,
            stage_id=self.id,
            stage_name=self.name,
        )


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


@pytest.fixture
def admin_client() -> AdminClient:
    return AdminClient({"bootstrap.servers": BOOTSTRAP_SERVERS})


@pytest.fixture
def topic(admin_client: AdminClient) -> Iterator[str]:
    topic_name = f"_smoke_test_{uuid.uuid4().hex}"

    new_topic = NewTopic(
        topic_name,
        num_partitions=1,
        replication_factor=1,
    )

    create_futures = admin_client.create_topics([new_topic])
    create_futures[topic_name].result(timeout=30)

    try:
        yield topic_name
    finally:
        delete_futures = admin_client.delete_topics([topic_name])
        delete_futures[topic_name].result(timeout=30)


@pytest.fixture
def provider_factory() -> ProviderFactory:
    return ProviderFactory(
        registry=bootstrap(),
        settings=Settings(),
    )


@pytest.fixture
def messaging_provider(
    provider_factory: ProviderFactory,
) -> MessagingProvider:
    return cast(
        MessagingProvider,
        provider_factory.create("kafka"),
    )


def create_context() -> ProcessingContext:
    return ProcessingContext(
        id="context-real-kafka-smoke-test",
        metadata=ExecutionMetadata(
            execution_id="execution-real-kafka-smoke-test",
        ),
    )


# ----------------------------------------------------------------------
# Scenario
# ----------------------------------------------------------------------


async def test_kafka_message_is_published_into_the_processing_context(
    messaging_provider: MessagingProvider,
    provider_factory: ProviderFactory,
    topic: str,
) -> None:
    group_id = f"smoke-test-group-{uuid.uuid4().hex}"

    messaging_provider.produce(
        topic,
        value=MESSAGE_VALUE,
        key=MESSAGE_KEY,
    )

    stage = MessageConsumingStage(
        id="consume-smoke-test-message",
        name="Consume Smoke Test Message",
        provider_name="kafka",
        topic=topic,
        group_id=group_id,
        max_attempts=15,
        provider_factory=provider_factory,
    )

    pipeline = Pipeline(
        id="messaging-smoke-test",
        name="Messaging Smoke Test",
        stages=(stage,),
    )

    context = create_context()

    result = await SequentialExecutor().execute(pipeline, context)

    assert result.status == ExecutionStatus.COMPLETED

    assert context.get(MessagingKeys.TOPIC) == topic
    assert context.get(MessagingKeys.KEY) == MESSAGE_KEY
    assert context.get(MessagingKeys.PARTITION) == 0
    assert context.get(MessagingKeys.OFFSET) == 0
    assert context.get(MessagingKeys.CONSUMER_GROUP) == group_id

    pipeline_result = context.get(ProcessingKeys.PIPELINE_RESULT)
    assert isinstance(pipeline_result, PipelineResult)
    assert pipeline_result is result
    assert pipeline_result.status == ExecutionStatus.COMPLETED
