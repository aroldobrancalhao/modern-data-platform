"""
Application configuration loader.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from jinja2 import Environment, StrictUndefined


class ConfigLoader:
    """
    Loads the bootstrap configuration from config.yaml.
    """

    def __init__(
        self,
        file_name: str = "config.yaml",
    ) -> None:
        self._file_path = Path(__file__).resolve().parent.parent / file_name

        self._jinja = Environment(
            undefined=StrictUndefined,
            autoescape=False,
        )

    def load(self) -> dict[str, Any]:
        """
        Loads the application configuration.

        Returns
        -------
        dict[str, Any]
            Configuration dictionary.
        """
        if not self._file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self._file_path}")

        load_dotenv()

        raw = self._file_path.read_text(
            encoding="utf-8",
        )

        rendered = self._jinja.from_string(raw).render(
            env=os.environ,
        )

        config = yaml.safe_load(rendered)

        if config is None:
            return {}

        if not isinstance(config, dict):
            raise ValueError("config.yaml must contain a dictionary at the root level.")

        return config
