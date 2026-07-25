from data_platform.processing.events.hook_type import HookType


def test_hook_type_values_are_stable() -> None:
    """Ensure enum values remain stable."""

    assert HookType.BEFORE_PIPELINE.value == "before_pipeline"
    assert HookType.AFTER_PIPELINE.value == "after_pipeline"
    assert HookType.PIPELINE_FAILED.value == "pipeline_failed"

    assert HookType.BEFORE_STAGE.value == "before_stage"
    assert HookType.AFTER_STAGE.value == "after_stage"
    assert HookType.STAGE_FAILED.value == "stage_failed"


def test_hook_type_is_string_enum() -> None:
    """HookType should behave as a string."""

    assert isinstance(HookType.BEFORE_STAGE.value, str)
    assert HookType.BEFORE_STAGE == "before_stage"