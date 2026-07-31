"""
Modern Data Platform
Processing Framework

Stage abstraction.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from data_platform.processing.core.entity import Entity
from data_platform.processing.core.processing_context import ProcessingContext
from data_platform.processing.core.stage_result import StageResult
from data_platform.providers.provider import Provider
from data_platform.providers.provider_factory import ProviderFactory


@dataclass(eq=False, slots=True)
class Stage(Entity[str], ABC):
    """
    Base abstraction for a processing stage.
    """

    name: str

    max_attempts: int = 3

    provider_factory: ProviderFactory | None = field(default=None)

    def resolve_provider(self, provider_name: str) -> Provider:
        """
        Resolves a Provider by name using the ProviderFactory injected
        into this Stage.

        Concrete stages call this from within ``execute(context)`` to
        obtain the Provider they need (e.g. ``self.resolve_provider(
        "aws.s3")``), instead of importing or instantiating a concrete
        Provider directly -- this keeps stages decoupled from any
        specific vendor implementation, consistent with ADR-010.

        Raises
        ------
        RuntimeError
            If this Stage was constructed without a ProviderFactory.
            This is a configuration error: whoever assembles the
            Pipeline must inject a ProviderFactory into every Stage
            that needs to resolve a Provider.
        """

        if self.provider_factory is None:
            raise RuntimeError(
                f"Stage '{self.name}' attempted to resolve provider "
                f"'{provider_name}', but no ProviderFactory was "
                "injected into this Stage. Pass a ProviderFactory "
                "when constructing the Stage."
            )

        return self.provider_factory.create(provider_name)

    @abstractmethod
    async def execute(
        self,
        context: ProcessingContext,
    ) -> StageResult:
        """
        Executes the stage.
        """
        raise NotImplementedError