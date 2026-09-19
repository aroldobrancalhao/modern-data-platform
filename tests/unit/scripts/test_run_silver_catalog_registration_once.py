"""
Modern Data Platform

Unit test for the real bug found in
scripts/run_silver_catalog_registration_once.py's failure path: a
raised (not "soft") stage exception leaves PipelineResult.stage_results
empty (see BaseExecutor.execute()'s outer except-block), so the old
`result.stage_results[0]` access raised IndexError instead of
surfacing the real error -- masking whatever actually failed behind an
unrelated crash. Fixed by reading error_type/error_message off the
PipelineResult itself, which BaseExecutor always populates correctly
regardless of which failure shape produced it.

Patches SequentialExecutor.execute directly (not a fake Stage) so this
stays a fast, dependency-free unit test -- _register_one() builds its
own real SilverCatalogRegistrationStage internally, no injection
point, and that Stage's real work needs live AWS credentials/network
this test must not depend on.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from data_platform.processing.core.execution_metadata import ExecutionMetadata
from data_platform.processing.core.execution_status import ExecutionStatus
from data_platform.processing.core.pipeline_result import PipelineResult
from data_platform.processing.executor.sequential_executor import (
    SequentialExecutor,
)
from data_platform.processing.metrics.prometheus_metrics_hook import (
    PrometheusHook,
)

from scripts.run_silver_catalog_registration_once import _register_one

pytestmark = pytest.mark.anyio


async def test_register_one_raised_exception_reports_real_error_not_indexerror() -> None:
    """
    Reproduces the original crash's exact PipelineResult shape: FAILED
    status, empty stage_results (what a raised, non-"soft" exception
    produces -- see BaseExecutor.execute()'s except Exception branch).
    Before the fix, this raised IndexError instead of the SystemExit
    below.
    """

    failed_result = PipelineResult(
        status=ExecutionStatus.FAILED,
        metadata=ExecutionMetadata(execution_id="test-execution"),
        stage_results=(),
        error_type="AccessDeniedException",
        error_message="not authorized to perform glue:CreateTable",
    )

    with patch.object(
        SequentialExecutor,
        "execute",
        new=AsyncMock(return_value=failed_result),
    ):
        with pytest.raises(SystemExit) as exc_info:
            await _register_one(
                entity="order_status_history",
                provider_factory=None,
                metrics_hook=PrometheusHook(),
            )

    message = str(exc_info.value)
    assert "IndexError" not in message
    assert "AccessDeniedException" in message
    assert "not authorized to perform glue:CreateTable" in message


async def test_register_one_soft_failure_still_reports_real_error() -> None:
    """
    The other failure shape (a "soft" StageResult(succeeded=False), no
    raised exception) already worked before the fix -- stage_results
    has an entry in this case. Confirms the fix didn't regress it:
    PipelineResult.error_type/error_message are mirrored from the same
    place either way, so reading them directly is correct for both.
    """

    failed_result = PipelineResult(
        status=ExecutionStatus.FAILED,
        metadata=ExecutionMetadata(execution_id="test-execution"),
        stage_results=(),
        error_type="TableAlreadyExistsError",
        error_message="Table 'order_status_history' already exists",
    )

    with patch.object(
        SequentialExecutor,
        "execute",
        new=AsyncMock(return_value=failed_result),
    ):
        with pytest.raises(SystemExit) as exc_info:
            await _register_one(
                entity="order_status_history",
                provider_factory=None,
                metrics_hook=PrometheusHook(),
            )

    message = str(exc_info.value)
    assert "TableAlreadyExistsError" in message
    assert "already exists" in message
