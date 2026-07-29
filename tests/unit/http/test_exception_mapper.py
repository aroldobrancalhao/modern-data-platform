from __future__ import annotations

import pytest

from data_platform.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    RateLimitError,
    RemoteServiceError,
    RemoteTimeoutError,
    ResourceNotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from data_platform.http.exception_mapper import HttpExceptionMapper
from data_platform.http.http_error import (
    HttpRequestError,
    HttpResponseError,
)


@pytest.mark.parametrize(
    ("status_code", "expected_exception"),
    [
        (400, ValidationError),
        (401, AuthenticationError),
        (403, AuthorizationError),
        (404, ResourceNotFoundError),
        (409, ConflictError),
        (429, RateLimitError),
        (500, RemoteServiceError),
        (502, RemoteServiceError),
        (503, ServiceUnavailableError),
    ],
)
def test_should_translate_http_response_error(
    status_code: int,
    expected_exception: type[RemoteServiceError],
) -> None:
    exception = HttpResponseError(
        status_code=status_code,
        message=f"HTTP {status_code}",
    )

    translated = HttpExceptionMapper.translate(
        exception,
    )

    assert isinstance(
        translated,
        expected_exception,
    )


def test_should_translate_request_error_to_remote_timeout() -> None:
    exception = HttpRequestError(
        "Connection timeout",
    )

    translated = HttpExceptionMapper.translate(
        exception,
    )

    assert isinstance(
        translated,
        RemoteTimeoutError,
    )


def test_should_preserve_original_message() -> None:
    exception = HttpResponseError(
        status_code=404,
        message="Workflow not found",
    )

    translated = HttpExceptionMapper.translate(
        exception,
    )

    assert isinstance(
        translated,
        ResourceNotFoundError,
    )

    assert str(translated) == "Workflow not found"


def test_should_translate_unknown_status_to_remote_service_error() -> None:
    exception = HttpResponseError(
        status_code=418,
        message="I'm a teapot",
    )

    translated = HttpExceptionMapper.translate(
        exception,
    )

    assert isinstance(
        translated,
        RemoteServiceError,
    )

    assert str(translated) == "I'm a teapot"