from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """
    Generic HTTP response.
    """

    status_code: int

    headers: dict[str, str]

    body: Any