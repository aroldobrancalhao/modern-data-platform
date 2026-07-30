from data_platform.http.http_error import (
    HttpRequestError,
    HttpResponseError,
)
from data_platform.http.exception_mapper import HttpExceptionMapper


class AirflowExceptionMapper:

    @staticmethod
    def translate(
        exception: HttpRequestError | HttpResponseError,
    ) -> Exception:

        return HttpExceptionMapper.translate(
            exception,
        )