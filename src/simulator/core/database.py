from contextlib import contextmanager
from typing import Generator

import psycopg
from psycopg import Connection

from simulator.core.settings import get_settings


class Database:
    def __init__(self) -> None:
        self._settings = get_settings()

    @contextmanager
    def connection(self) -> Generator[Connection, None, None]:
        connection = psycopg.connect(
            host=self._settings.postgres_host,
            port=self._settings.postgres_port,
            dbname=self._settings.postgres_database,
            user=self._settings.postgres_user,
            password=self._settings.postgres_password,
        )

        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
