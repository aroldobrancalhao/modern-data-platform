from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from data_platform.exceptions import (
    AuthenticationError,
    RemoteTimeoutError,
    ResourceNotFoundError,
)
from data_platform.http.http_error import (
    HttpRequestError,
    HttpResponseError,
)
from integrations.airflow.config.airflow_settings import AirflowSettings
from integrations.airflow.core import (
    AirflowClient,
    AirflowContext,
)


@pytest.fixture
def settings() -> AirflowSettings:
    return AirflowSettings(
        base_url="http://localhost:8080",
        username="airflow",
        password="airflow",
    )


@pytest.fixture
def http_client() -> MagicMock:
    return MagicMock()


@pytest.fixture
def client(
    settings: AirflowSettings,
    http_client: MagicMock,
) -> AirflowClient:

    context = AirflowContext(
        settings=settings,
        http=http_client,
    )

    return AirflowClient(
        context,
    )


def authentication_response():

    response = MagicMock()

    response.body = {
        "access_token": "jwt-token",
    }

    return response


def success_response():

    return MagicMock()


def test_should_authenticate_only_once(
    client: AirflowClient,
    http_client: MagicMock,
):

    http_client.post.return_value = authentication_response()

    http_client.request.return_value = success_response()

    client.list_dags()
    client.list_dags()

    assert http_client.post.call_count == 1


def test_should_retry_after_401(
    client: AirflowClient,
    http_client: MagicMock,
):

    http_client.post.return_value = authentication_response()

    http_client.request.side_effect = [
        HttpResponseError(
            401,
            "expired",
        ),
        success_response(),
    ]

    client.list_dags()

    assert http_client.request.call_count == 2

    assert http_client.post.call_count == 2


def test_should_translate_not_found_after_retry(
    client: AirflowClient,
    http_client: MagicMock,
):

    http_client.post.return_value = authentication_response()

    http_client.request.side_effect = [
        HttpResponseError(
            401,
            "expired",
        ),
        HttpResponseError(
            404,
            "not found",
        ),
    ]

    with pytest.raises(ResourceNotFoundError):
        client.list_dags()


def test_should_translate_authentication_error_after_retry(
    client: AirflowClient,
    http_client: MagicMock,
):

    http_client.post.return_value = authentication_response()

    http_client.request.side_effect = [
        HttpResponseError(
            401,
            "expired",
        ),
        HttpResponseError(
            401,
            "invalid",
        ),
    ]

    with pytest.raises(AuthenticationError):
        client.list_dags()


def test_should_translate_request_error(
    client: AirflowClient,
    http_client: MagicMock,
):

    http_client.post.return_value = authentication_response()

    http_client.request.side_effect = HttpRequestError(
        "timeout",
    )

    with pytest.raises(RemoteTimeoutError):
        client.list_dags()