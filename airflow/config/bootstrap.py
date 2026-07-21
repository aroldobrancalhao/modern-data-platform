"""
Bootstrap entrypoint.

This script initializes the Airflow environment by synchronizing:

- Connections
- Variables
- Pools

Usage:

    python airflow/config/bootstrap.py
"""

from bootstrap.bootstrap import Bootstrap


def main() -> None:
    Bootstrap().run()


if __name__ == "__main__":
    main()
