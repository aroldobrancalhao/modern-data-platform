"""
Modern Data Platform
Processing Framework

Unit tests for TracingHook.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from data_platform.processing.core.execution_metadata import (
    ExecutionMetadata,
)
from data_platform.processing.core.execution_status import (
    ExecutionStatus,
)
from data_platform.processing.core.pipeline import Pipeline
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)
from data_platform.processing.core.processing_result import (
    ProcessingResult,
)
from data_platform.processing.core.stage import Stage
from data_platform.processing.core.stage_result import (
    StageResult,
)
from data_platform.processing.events.hook_context import (
    HookContext,
)
from data_platform.processing.events.hook_type import (
    HookType,
)
from data_platform.processing.tracing.trace import Trace
from data_platform.processing.tracing.tracer import Tracer
from data_platform.processing.tracing.tracing_hook import (
    TracingHook,
)

pytestmark = pytest.mark.anyio


class DummyTracer(Tracer):

    def record(
        self,
        trace: Trace,
    ) -> None:
        self.trace = trace


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


def create_context() -> ProcessingContext:
    return ProcessingContext(
        id="context",
        metadata=ExecutionMetadata(
            execution_id="execution-1",
        ),
    )


def create_pipeline() -> Pipeline:
    return Pipeline(
        id="pipeline",
        name="Pipeline",
        stages=(
            DummyStage(
                id="extract",
                name="Extract",
            ),
            DummyStage(
                id="transform",
                name="Transform",
            ),
        ),
    )


def create_result(
    context: ProcessingContext,
) -> ProcessingResult:
    return ProcessingResult(
        status=ExecutionStatus.COMPLETED,
        metadata=context.metadata,
    )


async def test_should_record_completed_pipeline() -> None:

    tracer = Mock(spec=Tracer)

    hook = TracingHook(
        tracer=tracer,
    )

    context = create_context()
    pipeline = create_pipeline()

    await hook.execute(
        HookContext(
            hook_type=HookType.BEFORE_PIPELINE,
            pipeline=pipeline,
            processing_context=context,
        )
    )

    for stage in pipeline.stages:

        await hook.execute(
            HookContext(
                hook_type=HookType.BEFORE_STAGE,
                pipeline=pipeline,
                processing_context=context,
                stage=stage,
            )
        )

        await hook.execute(
            HookContext(
                hook_type=HookType.AFTER_STAGE,
                pipeline=pipeline,
                processing_context=context,
                stage=stage,
                result=create_result(context),
            )
        )

    await hook.execute(
        HookContext(
            hook_type=HookType.AFTER_PIPELINE,
            pipeline=pipeline,
            processing_context=context,
            result=create_result(context),
        )
    )

    tracer.record.assert_called_once()

    trace = tracer.record.call_args.args[0]

    assert trace.pipeline_id == "pipeline"
    assert trace.pipeline_name == "Pipeline"
    assert trace.execution_id == "execution-1"
    assert len(trace.spans) == 2


async def test_should_record_failed_stage() -> None:

    tracer = Mock(spec=Tracer)

    hook = TracingHook(
        tracer=tracer,
    )

    context = create_context()
    pipeline = create_pipeline()

    stage = pipeline.stages[0]

    await hook.execute(
        HookContext(
            hook_type=HookType.BEFORE_PIPELINE,
            pipeline=pipeline,
            processing_context=context,
        )
    )

    await hook.execute(
        HookContext(
            hook_type=HookType.BEFORE_STAGE,
            pipeline=pipeline,
            processing_context=context,
            stage=stage,
        )
    )

    await hook.execute(
        HookContext(
            hook_type=HookType.STAGE_FAILED,
            pipeline=pipeline,
            processing_context=context,
            stage=stage,
            exception=RuntimeError("failure"),
        )
    )

    await hook.execute(
        HookContext(
            hook_type=HookType.AFTER_PIPELINE,
            pipeline=pipeline,
            processing_context=context,
        )
    )

    tracer.record.assert_called_once()

    trace = tracer.record.call_args.args[0]

    assert len(trace.spans) == 1

    span = trace.spans[0]

    assert span.stage_id == "extract"
    assert span.exception == "failure"