from __future__ import annotations

from typing import Any

from data_platform.http import (
    HttpClient,
    HttpResponse,
)
from data_platform.http.http_error import HttpResponseError

from .airflow_context import AirflowContext


class AirflowClient:

    API_PREFIX = "/api/v2"

    def __init__(
        self,
        context: AirflowContext,
    ) -> None:

        self._http: HttpClient = context.http
        self._settings = context.settings

        self._access_token: str | None = None

    #
    # Authentication
    #

    def _authenticate(self) -> None:

        if self._access_token is not None:
            return

        response = self._http.post(
            "/auth/token",
            json={
                "username": self._settings.username,
                "password": self._settings.password,
            },
        )

        self._access_token = response.body["access_token"]

    def _clear_authentication(self) -> None:
        self._access_token = None

    def _authorization_headers(self) -> dict[str, str]:

        self._authenticate()

        return {
            "Authorization": f"Bearer {self._access_token}",
        }

    #
    # Request
    #

    def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> HttpResponse:

        kwargs["headers"] = self._authorization_headers()

        try:

            return self._http.request(
                method,
                path,
                **kwargs,
            )

        except HttpResponseError as ex:

            if ex.status_code != 401:
                raise

            #
            # JWT expired
            #

            self._clear_authentication()

            kwargs["headers"] = self._authorization_headers()

            return self._http.request(
                method,
                path,
                **kwargs)

    #
    # DAGs
    #

    def list_dags(self) -> HttpResponse:

        return self._request(
            "GET",
            f"{self.API_PREFIX}/dags",
        )

    def get_dag(
        self,
        dag_id: str,
    ) -> HttpResponse:

        return self._request(
            "GET",
            f"{self.API_PREFIX}/dags/{dag_id}",
        )

    #
    # Runs
    #

    def trigger_dag(
        self,
        dag_id: str,
        payload: dict[str, Any],
    ) -> HttpResponse:

        return self._request(
            "POST",
            f"{self.API_PREFIX}/dags/{dag_id}/dagRuns",
            json={
                "logical_date": None,
                "conf": payload,
            },
        )

    def list_dag_runs(
        self,
        dag_id: str,
    ) -> HttpResponse:

        return self._request(
            "GET",
            f"{self.API_PREFIX}/dags/{dag_id}/dagRuns",
        )

    def get_dag_run(
        self,
        workflow_id: str,
        run_id: str,
    ) -> HttpResponse:

        response = self._request(
            "GET",
            f"/api/v2/dags/{workflow_id}/dagRuns/{run_id}",
        )

        print("\n===== AIRFLOW DAG RUN =====")
        print(response.body)
        print("===========================\n")

        return response

    def cancel_dag_run(
        self,
        dag_id: str,
        run_id: str,
    ) -> HttpResponse:

        return self._request(
            "PATCH",
            f"{self.API_PREFIX}/dags/{dag_id}/dagRuns/{run_id}",
            json={
                "state": "failed",
            },
        )