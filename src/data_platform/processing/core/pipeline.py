"""
Modern Data Platform
Processing Framework

Pipeline definition.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from data_platform.processing.core.entity import Entity
from data_platform.processing.core.stage import Stage

# One or more Stages meant to run together. A lone Stage in
# `Pipeline.stages` is executed on its own; a nested tuple is a
# "parallel group" -- its members are independent of each other by
# convention (nothing here can verify that -- see `groups` below).
# Groups themselves still execute in sequence relative to each other
# and to any lone Stage around them.
StageGroup = tuple[Stage, ...]


@dataclass(
    eq=False,
    slots=True,
)
class Pipeline(Entity[str]):
    """
    Immutable processing pipeline.

    A Pipeline is an ordered collection of stages that defines the
    execution flow. An element of ``stages`` is either a lone
    ``Stage`` or a ``StageGroup`` (a nested tuple of Stages meant to
    run concurrently) -- see ``ParallelExecutor``. Grouping is purely
    a hint for executors that support it: ``SequentialExecutor``
    doesn't need to know groups exist at all, since iterating a
    Pipeline (``for stage in pipeline``, ``len(pipeline)``) always
    yields flat, individual Stages regardless of how they're grouped
    -- a grouped Pipeline run sequentially still produces a correct
    result (independent stages have no required order relative to
    each other), just without the concurrency benefit. Use ``groups``
    instead of iterating directly when an executor needs the group
    structure itself.
    """

    name: str

    stages: tuple[Stage | StageGroup, ...]

    def __post_init__(self) -> None:
        """
        Validates pipeline invariants.
        """
        if not self.id:
            raise ValueError("Pipeline id cannot be empty.")

        if not self.name:
            raise ValueError("Pipeline name cannot be empty.")

        if not self.stages:
            raise ValueError("A pipeline must contain at least one stage.")

        stage_ids: set[str] = set()

        for stage in self._flatten():
            if stage is None:
                raise ValueError("Pipeline cannot contain null stages.")

            if stage.id in stage_ids:
                raise ValueError(
                    f"Duplicate stage id detected: '{stage.id}'."
                )

            stage_ids.add(stage.id)

    def _flatten(self) -> Iterator[Stage | None]:
        # Return type includes None -- only __post_init__'s own
        # validation loop ever sees that case; any Pipeline in normal
        # use is already guaranteed to have none by the time __iter__
        # calls this.
        for item in self.stages:
            # None passes through unchanged rather than being iterated
            # (which would raise TypeError) -- __post_init__'s own
            # "stage is None" check is what turns it into the
            # intended ValueError.
            if item is None or isinstance(item, Stage):
                yield item
            else:
                yield from item

    def _flatten_validated(self) -> Iterator[Stage]:
        """
        Same traversal as ``_flatten()``, but a real ``Iterator[Stage]``
        -- every callsite other than ``__post_init__`` (which needs the
        raw ``None`` to raise its own descriptive ``ValueError``) uses
        this instead.

        The assertion below isn't just satisfying mypy: ``Pipeline``
        isn't ``frozen``, so ``stages`` could in principle be
        reassigned to include a ``None`` after construction, bypassing
        ``__post_init__``'s one-time validation entirely. An
        ``AssertionError`` here is a far clearer failure than silently
        handing a ``None`` downstream to whatever executor code calls
        this next.
        """
        for stage in self._flatten():
            assert stage is not None, "Pipeline cannot contain null stages."
            yield stage

    def __iter__(self) -> Iterator[Stage]:
        return self._flatten_validated()

    def __len__(self) -> int:
        return sum(1 for _ in self._flatten_validated())

    @property
    def is_empty(self) -> bool:
        return len(self.stages) == 0

    @property
    def stage_count(self) -> int:
        return len(self)

    @property
    def groups(self) -> tuple[StageGroup, ...]:
        """
        Normalized execution units: every element of ``stages`` as a
        tuple, wrapping a lone Stage into a 1-tuple. This is the view
        ``ParallelExecutor`` iterates -- each element runs as its own
        unit (concurrently within it, sequentially across units);
        ``SequentialExecutor`` doesn't use this, it iterates the
        Pipeline directly (see the class docstring).
        """
        return tuple(
            item if isinstance(item, tuple) else (item,)
            for item in self.stages
        )
