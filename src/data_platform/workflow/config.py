from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WorkflowConfig:
    """
    Base configuration for workflow providers.

    Concrete providers may extend this configuration with
    provider-specific settings.
    """