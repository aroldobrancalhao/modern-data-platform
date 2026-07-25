"""
Modern Data Platform
Processing Framework

Unit tests for PipelineBuilder.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import pytest

from data_platform.processing.core.execution_status import ExecutionStatus
from data_platform.processing.core.pipeline_builder import PipelineBuilder
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


def test_builder_uses_id_as_default_name() -> None:
    pipeline = (
        PipelineBuilder("pipeline")
        .add_stage(create_stage("extract"))
        .build()
    )

    assert pipeline.id == "pipeline"
    assert pipeline.name == "pipeline"


def test_builder_named_changes_name() -> None:
    pipeline = (
        PipelineBuilder("pipeline")
        .named("Customer Pipeline")
        .add_stage(create_stage("extract"))
        .build()
    )

    assert pipeline.name == "Customer Pipeline"


def test_builder_add_stage() -> None:
    stage = create_stage("extract")

    pipeline = (
        PipelineBuilder("pipeline")
        .add_stage(stage)
        .build()
    )

    assert pipeline.stage_count == 1
    assert pipeline.stages == (stage,)


def test_builder_add_stages() -> None:
    stage1 = create_stage("extract")
    stage2 = create_stage("transform")
    stage3 = create_stage("load")

    pipeline = (
        PipelineBuilder("pipeline")
        .add_stages(
            stage1,
            stage2,
            stage3,
        )
        .build()
    )

    assert pipeline.stage_count == 3

    assert pipeline.stages == (
        stage1,
        stage2,
        stage3,
    )


def test_builder_preserves_stage_order() -> None:
    stage1 = create_stage("one")
    stage2 = create_stage("two")
    stage3 = create_stage("three")

    pipeline = (
        PipelineBuilder("pipeline")
        .add_stages(
            stage1,
            stage2,
            stage3,
        )
        .build()
    )

    assert list(pipeline) == [
        stage1,
        stage2,
        stage3,
    ]


def test_builder_rejects_none_stage() -> None:
    builder = PipelineBuilder("pipeline")

    with pytest.raises(
        ValueError,
        match="Stage cannot be None.",
    ):
        builder.add_stage(None)  # type: ignore[arg-type]


def test_builder_build_without_name_uses_id() -> None:
    pipeline = (
        PipelineBuilder("customer_pipeline")
        .add_stage(create_stage("extract"))
        .build()
    )

    assert pipeline.name == "customer_pipeline"


def test_builder_build_without_stage_fails() -> None:
    with pytest.raises(
        ValueError,
        match="A pipeline must contain at least one stage.",
    ):
        (
            PipelineBuilder("pipeline")
            .build()
        )


def test_builder_supports_method_chaining() -> None:
    builder = (
        PipelineBuilder("pipeline")
        .named("Pipeline")
        .add_stage(create_stage("extract"))
    )

    pipeline = builder.build()

    assert pipeline.id == "pipeline"
    assert pipeline.name == "Pipeline"
    assert pipeline.stage_count == 1