from enum import Enum


class PolicyEvent(str, Enum):
    """
    Eventos conhecidos pelo Runtime.

    O Runtime informa em qual momento da execução
    uma Policy está sendo avaliada.
    """

    BEFORE_PIPELINE = "before_pipeline"

    AFTER_PIPELINE = "after_pipeline"

    BEFORE_STAGE = "before_stage"

    AFTER_STAGE = "after_stage"

    PIPELINE_FAILED = "pipeline_failed"

    STAGE_FAILED = "stage_failed"