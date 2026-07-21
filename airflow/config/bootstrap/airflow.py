"""
Airflow metadata synchronization.

Responsible for synchronizing:

- Connections
- Variables
- Pools
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from airflow.models import Connection
from airflow.models import Pool
from airflow.models import Variable
from airflow.settings import Session


class AirflowManager:
    def __init__(self) -> None:
        self._config_directory = Path(__file__).resolve().parent.parent

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def sync_connections(
        self,
        outputs: dict[str, Any],
    ) -> None:

        connections = self._build_connections(outputs)

        session = Session()

        try:
            for values in connections:
                conn_id = values["conn_id"]

                connection = self._get_connection(
                    session=session,
                    conn_id=conn_id,
                )

                if connection is None:
                    connection = Connection(**values)

                    self._save_connection(
                        session=session,
                        connection=connection,
                    )

                    continue

                self._update_connection(
                    connection=connection,
                    values=values,
                )

            session.commit()

        finally:
            session.close()

    def sync_variables(
        self,
        outputs: dict[str, Any],
        config: dict[str, Any],
    ) -> None:

        variables = {
            "environment": outputs["environment"],
            "aws_region": outputs["aws_region"],
            "datalake_bucket": outputs["datalake_bucket"],
            "bronze_database": outputs["bronze_database"],
            "silver_database": outputs["silver_database"],
            "gold_database": outputs["gold_database"],
            "athena_workgroup": outputs["athena_workgroup"],
            "bronze_path": "bronze/",
            "silver_path": "silver/",
            "gold_path": "gold/",
            "schemas_path": "schemas/",
            "logs_path": "logs/",
            "tmp_path": "tmp/",
            "checkpoints_path": "checkpoints/",
        }

        for key, value in variables.items():
            self._set_variable(
                key=key,
                value=value,
            )

        for key, value in config.items():
            self._set_variable(
                key=key,
                value=value,
            )

    def sync_pools(self) -> None:

        pools = self._load_pools()

        session = Session()

        try:
            for values in pools:
                name = values["name"]

                pool = self._get_pool(
                    session=session,
                    name=name,
                )

                if pool is None:
                    pool = Pool(
                        pool=name,
                        slots=values["slots"],
                        description=values.get("description", ""),
                        include_deferred=values.get(
                            "include_deferred",
                            False,
                        ),
                    )

                    self._save_pool(
                        session=session,
                        pool=pool,
                    )

                    continue

                self._update_pool(
                    pool=pool,
                    values=values,
                )

            session.commit()

        finally:
            session.close()

    # ------------------------------------------------------------------
    # Connection Builder
    # ------------------------------------------------------------------

    def _build_connections(
        self,
        outputs: dict[str, Any],
    ) -> list[dict[str, Any]]:

        return [
            {
                "conn_id": "aws_default",
                "conn_type": "aws",
                "description": "Default AWS connection",
                "extra": json.dumps(
                    {
                        "region_name": outputs["aws_region"],
                    }
                ),
            },
            {
                "conn_id": "postgres_marketplace",
                "conn_type": "postgres",
                "description": "Marketplace PostgreSQL",
                "host": self._env("POSTGRES_HOST"),
                "schema": self._env("POSTGRES_DB"),
                "login": self._env("POSTGRES_USER"),
                "password": self._env("POSTGRES_PASSWORD"),
                "port": self._env_int("POSTGRES_PORT"),
            },
            {
                "conn_id": "postgres_airflow",
                "conn_type": "postgres",
                "description": "Airflow Metadata Database",
                "host": self._env("AIRFLOW_DB_HOST"),
                "schema": self._env("AIRFLOW_DB_NAME"),
                "login": self._env("AIRFLOW_DB_USER"),
                "password": self._env("AIRFLOW_DB_PASSWORD"),
                "port": self._env_int("AIRFLOW_DB_PORT"),
            },
            {
                "conn_id": "kafka_default",
                "conn_type": "kafka",
                "description": "Kafka Bootstrap Server",
                "host": self._env("KAFKA_BOOTSTRAP_SERVER"),
            },
        ]

    # ------------------------------------------------------------------
    # Environment Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _env(name: str) -> str:

        value = os.getenv(name)

        if value is None:
            raise RuntimeError(f"Environment variable '{name}' is not defined.")

        return value

    @classmethod
    def _env_int(
        cls,
        name: str,
    ) -> int:

        return int(cls._env(name))

    # ------------------------------------------------------------------
    # Pool Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _save_pool(
        session: Session,
        pool: Pool,
    ) -> None:

        session.add(pool)

    @staticmethod
    def _update_pool(
        pool: Pool,
        values: dict[str, Any],
    ) -> None:

        pool.slots = values["slots"]

        pool.description = values.get(
            "description",
            "",
        )

        pool.include_deferred = values.get(
            "include_deferred",
            False,
        )

    # ------------------------------------------------------------------
    # Connection Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_connection(
        session: Session,
        conn_id: str,
    ) -> Connection | None:

        return (
            session.query(Connection)
            .filter(Connection.conn_id == conn_id)
            .one_or_none()
        )

    @staticmethod
    def _save_connection(
        session: Session,
        connection: Connection,
    ) -> None:

        session.add(connection)

    @staticmethod
    def _update_connection(
        connection: Connection,
        values: dict[str, Any],
    ) -> None:

        for key, value in values.items():
            setattr(connection, key, value)

    # ------------------------------------------------------------------
    # Variable Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _set_variable(
        key: str,
        value: Any,
    ) -> None:

        Variable.set(
            key=key,
            value=value,
            serialize_json=isinstance(value, (dict, list)),
        )

    # ------------------------------------------------------------------
    # Pool Helpers
    # ------------------------------------------------------------------

    def _load_pools(
        self,
    ) -> list[dict[str, Any]]:

        pools_file = self._config_directory / "pools.json"

        with pools_file.open(
            mode="r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    @staticmethod
    def _get_pool(
        session: Session,
        name: str,
    ) -> Pool | None:

        return session.query(Pool).filter(Pool.pool == name).one_or_none()
