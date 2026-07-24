from __future__ import annotations

from tests.unit.processing.shared.services.fake_processing_service import (
    FakeProcessingService,
)


def test_processing_execution_order(
    processing_context,
) -> None:
    service = FakeProcessingService()

    result = service.run(processing_context)

    assert result.success is True

    assert service.calls == [
        "before",
        "read",
        "transform",
        "write",
        "build_result",
        "after",
    ]