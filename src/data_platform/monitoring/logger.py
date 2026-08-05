from typing import Any

import structlog


def get_logger(name: str) -> Any:
    return structlog.get_logger(name)
