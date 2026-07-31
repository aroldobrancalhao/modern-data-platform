"""
Modern Data Platform
Processing Framework

Unit tests for Stage provider resolution (Fase 3 of the ADR-010
consolidation roadmap: connecting the ProviderRegistry to the
execution runtime).

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import pytest

from data_platform.config.settings import Settings
from data_platform.processing.core.execution_metadata import (
    ExecutionMetadata,
)
from data_platform.processing.core.context_keys.processing_keys import (
    ProcessingKeys,
)
from data_platform.processing.core.execution_status import ExecutionStatus
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)
from data_platform.processing.core.stage import Stage
from data_platform.processing.core.stage_result import StageResult
from data_platform.providers.provider import Provider
from data_platform.providers.provider_builder import ProviderBuilder
from data_platform.providers.provider_factory import ProviderFactory
from data_platform.providers.provider_registry import ProviderRegistry

pytestmark = pytest.mark.anyio


class FakeProvider(Provider):
    """
    Minimal concrete Provider used only to prove that a Stage can
    resolve a Provider through its injected ProviderFactory, without
    depending on any real (AWS/Databricks/Airflow) Provider or SDK.
    """


class FakeProviderBuilder(ProviderBuilder[FakeProvider]):
    def build(self) -> FakeProvider:
        return FakeProvider()


class ProviderResolvingStage(Stage):
    """
    Minimal concrete Stage used only to prove that ``resolve_provider``
    is usable from within ``execute(context)``, as intended for the
    concrete Stages that Fase 4 will implement.
    """

    async def execute(
        self,
        context: ProcessingContext,
    ) -> StageResult:

        provider = self.resolve_provider("fake")

        context.set(
            ProcessingKeys.OUTPUT,
            type(provider).__name__,
        )

        return StageResult(
            status=ExecutionStatus.COMPLETED,
            metadata=context.metadata,
            stage_id=self.id,
            stage_name=self.name,
        )


def create_context() -> ProcessingContext:
    return ProcessingContext(
        id="context-1",
        metadata=ExecutionMetadata(execution_id="execution-1"),
    )


def create_provider_factory() -> ProviderFactory:
    registry = ProviderRegistry()

    registry.register("fake", FakeProviderBuilder)

    return ProviderFactory(
        registry=registry,
        settings=Settings(),
    )


def test_resolve_provider_returns_instance_built_by_the_factory() -> None:
    stage = ProviderResolvingStage(
        id="s1",
        name="S1",
        provider_factory=create_provider_factory(),
    )

    provider = stage.resolve_provider("fake")

    assert isinstance(provider, FakeProvider)


def test_resolve_provider_raises_when_factory_not_injected() -> None:
    stage = ProviderResolvingStage(
        id="s1",
        name="S1",
    )

    with pytest.raises(RuntimeError, match="no ProviderFactory"):
        stage.resolve_provider("fake")


def test_stage_without_provider_factory_defaults_to_none() -> None:
    stage = ProviderResolvingStage(
        id="s1",
        name="S1",
    )

    assert stage.provider_factory is None


async def test_stage_execute_resolves_provider_through_injected_factory() -> None:
    stage = ProviderResolvingStage(
        id="s1",
        name="S1",
        provider_factory=create_provider_factory(),
    )

    context = create_context()

    result = await stage.execute(context)

    assert result.status == ExecutionStatus.COMPLETED
    assert context.get(ProcessingKeys.OUTPUT) == "FakeProvider"