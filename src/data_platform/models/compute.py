from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from enum import StrEnum
from enum import auto
from typing import Any


class ExecutionStatus(StrEnum):
    PENDING = auto()
    RUNNING = auto()
    SUCCEEDED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass(slots=True, frozen=True)
class Workload:
    """
    Represents a logical workload independently of the execution engine.
    """

    identifier: str
    parameters: Mapping[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class Execution:
    """
    Represents the execution of a workload.
    """

    execution_id: str
    status: ExecutionStatus