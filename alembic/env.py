"""
Uses `postgresql+psycopg://` (psycopg v3), same driver as the rest of
the app -- SQLAlchemy 2.0 is what apache-airflow-core (3.3.0+) resolves
to in this venv, and 2.0 is the first SQLAlchemy version with a v3
dialect at all. Alembic ran on psycopg2 for a while before that (see
git history), specifically because SQLAlchemy was pinned below 2.0 back
then.

There are no ORM models in this codebase (raw psycopg3 SQL everywhere),
so `target_metadata` stays None -- `autogenerate` has nothing to diff
against and isn't used; migrations here are written by hand.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from integrations.postgres.config import PostgresSettings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

_postgres_settings = PostgresSettings()
config.set_main_option(
    "sqlalchemy.url",
    f"postgresql+psycopg://{_postgres_settings.user}:{_postgres_settings.password}"
    f"@{_postgres_settings.host}:{_postgres_settings.port}/{_postgres_settings.database}",
)

# No ORM models in this codebase -- see module docstring above.
target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
