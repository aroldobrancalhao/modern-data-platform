from __future__ import annotations

import pytest

from integrations.postgres.config.postgres_settings import PostgresSettings

ENV_VARS = (
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DATABASE",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def test_defaults_match_the_local_docker_compose_stack() -> None:
    settings = PostgresSettings()

    assert settings.host == "localhost"
    assert settings.port == 5432
    assert settings.database == "marketplace"
    assert settings.user == "postgres"
    assert settings.password == "postgres"


def test_settings_are_overridden_by_environment_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("POSTGRES_HOST", "postgres-marketplace")
    monkeypatch.setenv("POSTGRES_PORT", "6543")
    monkeypatch.setenv("POSTGRES_DATABASE", "other_db")
    monkeypatch.setenv("POSTGRES_USER", "other_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "other_password")

    settings = PostgresSettings()

    assert settings.host == "postgres-marketplace"
    assert settings.port == 6543
    assert settings.database == "other_db"
    assert settings.user == "other_user"
    assert settings.password == "other_password"
