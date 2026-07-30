from unittest.mock import patch

from data_platform.http.exception_mapper import HttpExceptionMapper
from data_platform.http.http_error import (
    HttpRequestError,
    HttpResponseError,
)
from integrations.airflow.core.airflow_exception_mapper import (
    AirflowExceptionMapper,
)


class TestAirflowExceptionMapper:

    def test_should_delegate_http_request_error_to_http_exception_mapper(self):
        exception = HttpRequestError(
            "Connection failed",
        )

        translated = RuntimeError(
            "translated",
        )

        with patch.object(
            HttpExceptionMapper,
            "translate",
            return_value=translated,
        ) as translate:

            result = AirflowExceptionMapper.translate(
                exception,
            )

        translate.assert_called_once_with(
            exception,
        )

        assert result is translated

    def test_should_delegate_http_response_error_to_http_exception_mapper(self):
        exception = HttpResponseError(
            status_code=500,
            message="Internal Server Error",
        )

        translated = RuntimeError(
            "translated",
        )

        with patch.object(
            HttpExceptionMapper,
            "translate",
            return_value=translated,
        ) as translate:

            result = AirflowExceptionMapper.translate(
                exception,
            )

        translate.assert_called_once_with(
            exception,
        )

        assert result is translated