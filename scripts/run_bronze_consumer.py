"""
Modern Data Platform

Long-running process: runs the Bronze Consumer
(``streaming.consumers.bronze_consumer.run_bronze_consumer``) against
the real local Kafka broker, landing Debezium change events into the
real Bronze Delta tables (``bronze/{entity}/``) as they arrive.

Unlike the ``run_*_once.py`` scripts in this directory, this process
never exits on its own -- it is the streaming half of ADR-0008's flow,
independent from Airflow (see the Bronze Consumer module's own
docstring for the full picture, including this phase's known
limitations: no DLQ, no distributed lock against the batch flow).

Run with:

    PYTHONPATH=src uv run python scripts/run_bronze_consumer.py

(``PYTHONPATH=src`` is required outside pytest -- see "src/ packages
aren't installable -- PYTHONPATH required outside pytest" in
docs/architecture/roadmap-next-steps.md.)

Stop with Ctrl+C -- any micro-batch already flushed to Delta stays
committed; a batch still buffered in-process at the time of the
interrupt is replayed from the last committed offset next run.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from typing import cast

from data_platform.bootstrap import bootstrap
from data_platform.config.settings import Settings
from data_platform.messaging.messaging_provider import MessagingProvider
from data_platform.monitoring.logger import get_logger
from data_platform.observability.logging_config import configure_logging
from data_platform.providers.provider_factory import ProviderFactory

from streaming.consumers.bronze_consumer import run_bronze_consumer

logger = get_logger(__name__)


def main() -> None:
    configure_logging()

    provider_factory = ProviderFactory(
        registry=bootstrap(),
        settings=Settings(),
    )

    provider = cast(
        MessagingProvider,
        provider_factory.create("kafka"),
    )

    logger.info("Bronze Consumer starting.")

    try:
        run_bronze_consumer(provider)
    except KeyboardInterrupt:
        logger.info("Bronze Consumer stopped.")


if __name__ == "__main__":
    main()
