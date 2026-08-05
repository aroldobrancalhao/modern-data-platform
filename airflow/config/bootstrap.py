"""
Bootstrap entrypoint.

This script initializes the Airflow environment by synchronizing:

- Connections
- Variables
- Pools

Usage:

    python airflow/config/bootstrap.py
"""

import sys

if "/opt/mdp/src" not in sys.path:
    sys.path.insert(0, "/opt/mdp/src")

from bootstrap.bootstrap import Bootstrap
from data_platform.observability.logging_config import configure_logging


def main() -> None:
    configure_logging()

    Bootstrap().run()


if __name__ == "__main__":
    main()
