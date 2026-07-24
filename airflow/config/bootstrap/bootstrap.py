"""
Bootstrap orchestration.

Execution flow:

    ConfigLoader
        ↓
    TerraformOutputs
        ↓
    AirflowManager
            ├── Connections
            ├── Variables
            └── Pools
"""

from __future__ import annotations

import logging

from bootstrap.airflow import AirflowManager
from bootstrap.config import ConfigLoader
from bootstrap.terraform import TerraformOutputs

logger = logging.getLogger(__name__)


class Bootstrap:
    def __init__(self) -> None:
        self._config_loader = ConfigLoader()
        self._terraform_loader = TerraformOutputs()
        self._airflow_manager = AirflowManager()

    def run(self) -> None:
        logger.info("Starting Airflow bootstrap...")

        config = self._load_config()
        outputs = self._load_terraform_outputs()

        self._configure_connections(outputs)

        self._configure_variables(
            outputs=outputs,
            config=config,
        )

        self._configure_pools()

        logger.info("Airflow bootstrap completed successfully.")

    def _load_config(self) -> dict:
        logger.info("Loading configuration...")

        return self._config_loader.load()

    def _load_terraform_outputs(self) -> dict:
        logger.info("Loading Terraform outputs...")

        return self._terraform_loader.load()

    def _configure_connections(
        self,
        outputs: dict,
    ) -> None:
        logger.info("Synchronizing Airflow Connections...")

        self._airflow_manager.sync_connections(outputs)

    def _configure_variables(
        self,
        outputs: dict,
        config: dict,
    ) -> None:
        logger.info("Synchronizing Airflow Variables...")

        self._airflow_manager.sync_variables(
            outputs=outputs,
            config=config,
        )

    def _configure_pools(self) -> None:
        logger.info("Synchronizing Airflow Pools...")

        self._airflow_manager.sync_pools()

