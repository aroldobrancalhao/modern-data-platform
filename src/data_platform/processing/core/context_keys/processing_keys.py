from enum import StrEnum, unique


@unique
class ProcessingKeys(StrEnum):
    """Keys that describe the mutable processing state."""

    CURRENT_STAGE = "processing.current_stage"

    CURRENT_ATTEMPT = "processing.current_attempt"
    MAX_ATTEMPTS = "processing.max_attempts"

    EXCEPTION = "processing.exception"

    PIPELINE_RESULT = "processing.pipeline_result"
    STAGE_RESULT = "processing.stage_result"

    INPUT = "processing.input"
    OUTPUT = "processing.output"

    CANCELLED = "processing.cancelled"