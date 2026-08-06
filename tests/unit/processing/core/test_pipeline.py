"""
Modern Data Platform
Processing Framework

Unit tests for Pipeline.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import pytest

from data_platform.processing.core.execution_status import ExecutionStatus
from data_platform.processing.core.pipeline import Pipeline
from data_platform.processing.core.processing_context import ProcessingContext
from data_platform.processing.core.stage import Stage
from data_platform.processing.core.stage_result import StageResult


class DummyStage(Stage):
    async def execute(
        self,
        context: ProcessingContext,
    ) -> StageResult:
        return StageResult(
            status=ExecutionStatus.COMPLETED,
            metadata=context.metadata,
            stage_id=self.id,
            stage_name=self.name,
        )


def create_stage(identifier: str) -> DummyStage:
    return DummyStage(
        id=identifier,
        name=f"Stage {identifier}",
    )


def test_pipeline_is_created() -> None:
    stage = create_stage("extract")

    pipeline = Pipeline(
        id="pipeline",
        name="Pipeline",
        stages=(stage,),
    )

    assert pipeline.id == "pipeline"
    assert pipeline.name == "Pipeline"
    assert pipeline.stages == (stage,)


def test_pipeline_requires_id() -> None:
    stage = create_stage("extract")

    with pytest.raises(
        ValueError,
        match="Pipeline id cannot be empty.",
    ):
        Pipeline(
            id="",
            name="Pipeline",
            stages=(stage,),
        )


def test_pipeline_requires_name() -> None:
    stage = create_stage("extract")

    with pytest.raises(
        ValueError,
        match="Pipeline name cannot be empty.",
    ):
        Pipeline(
            id="pipeline",
            name="",
            stages=(stage,),
        )


def test_pipeline_requires_at_least_one_stage() -> None:
    with pytest.raises(
        ValueError,
        match="A pipeline must contain at least one stage.",
    ):
        Pipeline(
            id="pipeline",
            name="Pipeline",
            stages=(),
        )


def test_pipeline_rejects_none_stage() -> None:
    with pytest.raises(
        ValueError,
        match="Pipeline cannot contain null stages.",
    ):
        Pipeline(
            id="pipeline",
            name="Pipeline",
            stages=(None,),  # type: ignore[arg-type]
        )


def test_pipeline_rejects_duplicate_stage_ids() -> None:
    stage1 = create_stage("extract")
    stage2 = create_stage("extract")

    with pytest.raises(
        ValueError,
        match="Duplicate stage id detected: 'extract'.",
    ):
        Pipeline(
            id="pipeline",
            name="Pipeline",
            stages=(stage1, stage2),
        )


def test_pipeline_len_returns_stage_count() -> None:
    pipeline = Pipeline(
        id="pipeline",
        name="Pipeline",
        stages=(
            create_stage("one"),
            create_stage("two"),
            create_stage("three"),
        ),
    )

    assert len(pipeline) == 3


def test_pipeline_stage_count_property() -> None:
    pipeline = Pipeline(
        id="pipeline",
        name="Pipeline",
        stages=(
            create_stage("one"),
            create_stage("two"),
        ),
    )

    assert pipeline.stage_count == 2


def test_pipeline_is_not_empty() -> None:
    pipeline = Pipeline(
        id="pipeline",
        name="Pipeline",
        stages=(create_stage("extract"),),
    )

    assert pipeline.is_empty is False


def test_pipeline_is_iterable() -> None:
    stage1 = create_stage("extract")
    stage2 = create_stage("transform")

    pipeline = Pipeline(
        id="pipeline",
        name="Pipeline",
        stages=(stage1, stage2),
    )

    assert list(pipeline) == [
        stage1,
        stage2,
    ]


# ============================================================================
# StageGroup / flattening -- see ParallelExecutor
# ============================================================================


def test_iterating_a_grouped_pipeline_flattens_it() -> None:
    """
    A nested tuple (a parallel group) yields its members in order when
    the Pipeline is iterated directly -- this is what lets
    SequentialExecutor run a grouped Pipeline correctly without any
    changes of its own (it just sees a longer flat sequence).
    """

    before = create_stage("before")
    group_a = create_stage("group-a")
    group_b = create_stage("group-b")
    after = create_stage("after")

    pipeline = Pipeline(
        id="pipeline",
        name="Pipeline",
        stages=(before, (group_a, group_b), after),
    )

    assert list(pipeline) == [before, group_a, group_b, after]


def test_len_counts_individual_stages_not_top_level_elements() -> None:
    pipeline = Pipeline(
        id="pipeline",
        name="Pipeline",
        stages=(
            create_stage("before"),
            (create_stage("group-a"), create_stage("group-b")),
        ),
    )

    assert len(pipeline) == 3
    assert pipeline.stage_count == 3


def test_groups_wraps_lone_stages_into_1_tuples() -> None:
    lone = create_stage("lone")
    group_a = create_stage("group-a")
    group_b = create_stage("group-b")

    pipeline = Pipeline(
        id="pipeline",
        name="Pipeline",
        stages=(lone, (group_a, group_b)),
    )

    assert pipeline.groups == (
        (lone,),
        (group_a, group_b),
    )


def test_groups_on_an_ungrouped_pipeline_is_every_stage_alone() -> None:
    stage1 = create_stage("one")
    stage2 = create_stage("two")

    pipeline = Pipeline(
        id="pipeline",
        name="Pipeline",
        stages=(stage1, stage2),
    )

    assert pipeline.groups == ((stage1,), (stage2,))


def test_pipeline_rejects_none_stage_inside_a_group() -> None:
    with pytest.raises(
        ValueError,
        match="Pipeline cannot contain null stages.",
    ):
        Pipeline(
            id="pipeline",
            name="Pipeline",
            stages=((create_stage("a"), None),),  # type: ignore[arg-type]
        )


def test_pipeline_rejects_duplicate_stage_ids_across_a_group_and_a_lone_stage() -> (
    None
):
    with pytest.raises(
        ValueError,
        match="Duplicate stage id detected: 'extract'.",
    ):
        Pipeline(
            id="pipeline",
            name="Pipeline",
            stages=(
                (create_stage("extract"), create_stage("transform")),
                create_stage("extract"),
            ),
        )