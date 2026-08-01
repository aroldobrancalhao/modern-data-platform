"""
Modern Data Platform
Processing Framework

Publishes MessagingProvider results into the ProcessingContext.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from data_platform.messaging.models import Message
from data_platform.processing.core.context_keys.messaging_keys import (
    MessagingKeys,
)
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)


class MessagingContextWriter:
    """
    Translates a Message into MessagingKeys and publishes it into the
    ProcessingContext.

    This class knows about Message (a provider-agnostic domain model)
    and about ProcessingContext/MessagingKeys. It does not know about
    any concrete MessagingProvider (Kafka, MSK, Event Hubs, Pub/Sub,
    ...) -- the caller is responsible for obtaining the Message from a
    Provider (e.g. ``provider.consume(...)``) and passing it here.

    MessagingKeys.TOPIC is always populated, since Message always
    carries it. MessagingKeys.KEY is populated only when
    ``message.key`` is not None -- Kafka messages can legitimately
    have no key, and leaving the ContextKey unset in that case mirrors
    how WorkflowContextWriter treats WorkflowRun.workflow_name (also a
    required-but-nullable field). MessagingKeys.PARTITION and OFFSET
    are populated only when present on the Message: always the case
    for a Message returned by ``consume()``, absent for one built
    before producing.

    MessagingKeys.MESSAGE_ID is intentionally never set: Kafka has no
    broker-level "message id" concept -- a message is identified by
    its (topic, partition, offset) triple, which the other keys
    already capture. Populating MESSAGE_ID would mean inventing a
    value the Message model doesn't carry, the same "don't invent
    data" rule ComputeContextWriter follows for the fields Execution
    doesn't carry.

    MessagingKeys.CONSUMER_GROUP is not part of Message (it is a
    parameter of *consumption*, not a property of the message
    itself), so it is published only when the caller passes an
    explicit ``group_id`` -- mirroring how StorageContextWriter and
    ComputeContextWriter accept extra, non-domain-model context as
    separate parameters (``storage_object=``, the ``workload``
    argument).
    """

    @staticmethod
    def write(
        message: Message,
        context: ProcessingContext,
        *,
        group_id: str | None = None,
    ) -> None:
        """
        Publishes a Message into the ProcessingContext.

        Parameters
        ----------
        message:
            The Message returned by ``provider.consume(...)``, or
            built by the caller before ``provider.produce(...)``.

        context:
            The ProcessingContext of the current execution.

        group_id:
            The consumer group used to obtain ``message``, when
            applicable (i.e. after a ``consume()`` call). Published
            as MessagingKeys.CONSUMER_GROUP only when provided.
        """

        context.set(
            MessagingKeys.TOPIC,
            message.topic,
        )

        if message.key is not None:
            context.set(
                MessagingKeys.KEY,
                message.key,
            )

        if message.partition is not None:
            context.set(
                MessagingKeys.PARTITION,
                message.partition,
            )

        if message.offset is not None:
            context.set(
                MessagingKeys.OFFSET,
                message.offset,
            )

        if group_id is not None:
            context.set(
                MessagingKeys.CONSUMER_GROUP,
                group_id,
            )
