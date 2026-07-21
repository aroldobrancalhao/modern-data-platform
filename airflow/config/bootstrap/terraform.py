"""
Terraform outputs loader.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TerraformOutputs:
    """
    Loads Terraform outputs from terraform_outputs.json.

    Terraform exports values in the following format:

    {
        "aws_region": {
            "value": "sa-east-1",
            "type": "string"
        }
    }

    This class converts it into:

    {
        "aws_region": "sa-east-1"
    }
    """

    def __init__(
        self,
        file_name: str = "terraform_outputs.json",
    ) -> None:
        self._file_path = Path(__file__).resolve().parent.parent / file_name

    def load(self) -> dict[str, Any]:
        """
        Loads and normalizes Terraform outputs.

        Returns
        -------
        dict[str, Any]
            Flattened Terraform outputs.
        """
        if not self._file_path.exists():
            raise FileNotFoundError(
                f"Terraform outputs file not found: {self._file_path}"
            )

        with self._file_path.open(
            mode="r",
            encoding="utf-8",
        ) as file:
            raw_outputs = json.load(file)

        return self._normalize(raw_outputs)

    @staticmethod
    def _normalize(
        outputs: dict[str, Any],
    ) -> dict[str, Any]:
        normalized: dict[str, Any] = {}

        for key, value in outputs.items():
            if isinstance(value, dict) and "value" in value:
                normalized[key] = value["value"]
            else:
                normalized[key] = value

        return normalized
