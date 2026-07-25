"""
Modern Data Platform
Processing Framework

Statistics root object.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass

from data_platform.processing.core.value_object import ValueObject
from data_platform.processing.statistics.pipeline_statistics import (
    PipelineStatistics,
)


@dataclass(
    frozen=True,
    eq=False,
    slots=True,
)
class Statistics(ValueObject):
    """
    Root statistics object.

    Encapsulates pipeline execution statistics and serves
    as the entry point for future statistics extensions.
    """

    pipeline: PipelineStatistics