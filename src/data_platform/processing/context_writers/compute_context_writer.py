"""
Modern Data Platform
Processing Framework

Publishes ComputeProvider results into the ProcessingContext.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from data_platform.models.compute import Execution, Workload
from data_platform.processing.core.context_keys.compute_keys import (
    ComputeKeys,
)
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)


class ComputeContextWriter:
    """
    Translates a Workload/Execution pair into ComputeKeys and publishes
    them into the ProcessingContext.

    This class knows about Workload/Execution (provider-agnostic domain
    models) and about ProcessingContext/ComputeKeys. It does not know
    about any concrete ComputeProvider (Databricks, EMR, Glue Jobs,
    ...) -- the caller is responsible for obtaining the Execution from
    a Provider and passing it here together with the Workload that
    originated it.

    Only ComputeKeys.JOB_ID and ComputeKeys.RUN_ID are populated today.
    ComputeKeys.JOB_NAME, SESSION_ID, APPLICATION_ID and CLUSTER_ID are
    intentionally left unset: the current ``Execution`` domain model
    (``data_platform.models.compute.Execution``) only carries
    ``execution_id`` and ``status`` -- it does not carry those fields.
    Populating them would require extending ``Execution`` and
    ``DatabricksComputeMapper.to_execution`` to read that information
    from the Databricks SDK ``Run`` object, which is a Provider/Mapper
    change, out of scope here.
    """

    @staticmethod
    def write(
        workload: Workload,
        execution: Execution,
        context: ProcessingContext,
    ) -> None:
        """
        Publishes a Workload/Execution pair into the ProcessingContext.

        Parameters
        ----------
        workload:
            The Workload submitted to the ComputeProvider (e.g. the
            argument passed to ``provider.execute(workload)``).

        execution:
            The Execution returned by ``provider.execute(workload)``.

        context:
            The ProcessingContext of the current execution.
        """

        context.set(
            ComputeKeys.JOB_ID,
            workload.identifier,
        )

        context.set(
            ComputeKeys.RUN_ID,
            execution.execution_id,
        )