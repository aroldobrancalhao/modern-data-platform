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