from enum import StrEnum, unique


@unique
class ComputeKeys(StrEnum):
    """Keys produced by compute providers."""

    JOB_ID = "compute.job_id"
    JOB_NAME = "compute.job_name"

    RUN_ID = "compute.run_id"

    SESSION_ID = "compute.session_id"

    APPLICATION_ID = "compute.application_id"

    CLUSTER_ID = "compute.cluster_id"