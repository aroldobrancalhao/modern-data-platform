from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Workflow:
    """
    Represents a logical workflow definition.

    A Workflow is a platform abstraction and does not represent
    any provider-specific implementation (Airflow DAG, Prefect Flow,
    Dagster Job, etc.).

    Concrete providers are responsible for mapping this model to
    their native workflow definitions.
    """

    identifier: str

    name: str

    description: str | None = None

    parameters: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        """
        Backward-compatible alias for identifier.
        """
        return self.identifier