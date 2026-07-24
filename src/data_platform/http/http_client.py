from __future__ import annotations

from typing import Any

import httpx

from data_platform.http.http_error import (
    HttpRequestError,
    HttpResponseError,
)
from data_platform.http.http_response import HttpResponse


class HttpClient:
    """
    Generic synchronous HTTP client.

    This class is intentionally transport-only.
    Authentication is the responsibility of each integration
    (Airflow, Databricks, GitHub, Azure, etc.).
    """

    def __init__(
        self,
        *,
        base_url: str,
        timeout: int = 30,
        verify_ssl: bool = True,
        headers: dict[str, str] | None = None,
    ) -> None:

        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            verify=verify_ssl,
            headers=headers,
        )

    def request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> HttpResponse:
        return self._request(
            method,
            path,
            **kwargs,
        )

    def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:

        return self.request(
            "GET",
            path,
            params=params,
            headers=headers,
        )

    def post(
        self,
        path: str,
        *,
        json: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:

        return self.request(
            "POST",
            path,
            json=json,
            headers=headers,
        )

    def put(
        self,
        path: str,
        *,
        json: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:

        return self.request(
            "PUT",
            path,
            json=json,
            headers=headers,
        )

    def patch(
        self,
        path: str,
        *,
        json: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:

        return self.request(
            "PATCH",
            path,
            json=json,
            headers=headers,
        )

    def delete(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:

        return self.request(
            "DELETE",
            path,
            headers=headers,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HttpClient":
        return self

    def __exit__(
        self,
        exc_type: object,
        exc: object,
        traceback: object,
    ) -> None:
        self.close()

    def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> HttpResponse:

        try:

            response = self._client.request(
                method,
                path,
                **kwargs,
            )

        except httpx.RequestError as exc:
            raise HttpRequestError(str(exc)) from exc

        if response.is_error:
            raise HttpResponseError(
                response.status_code,
                response.text,
            )

        try:
            body = response.json()

        except ValueError:
            body = response.text

        return HttpResponse(
            status_code=response.status_code,
            headers=dict(response.headers),
            body=body,
        )