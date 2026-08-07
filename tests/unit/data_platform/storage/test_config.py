from __future__ import annotations

from data_platform.storage.config import StorageConfig, StorageSettings


def test_default_bucket_is_the_project_data_lake_bucket() -> None:
    assert (
        StorageSettings().default_bucket
        == "mdp-datalake-dev-857854758128"
    )


def test_raw_returns_the_raw_layer_uri() -> None:
    assert StorageConfig.raw("customers") == (
        "s3://mdp-datalake-dev-857854758128/raw/customers"
    )


def test_bronze_returns_the_bronze_layer_uri() -> None:
    assert StorageConfig.bronze("customers") == (
        "s3://mdp-datalake-dev-857854758128/bronze/customers"
    )


def test_bronze_batch_returns_a_separate_uri_from_bronze() -> None:
    assert StorageConfig.bronze_batch("customers") == (
        "s3://mdp-datalake-dev-857854758128/bronze_batch/customers"
    )
    assert StorageConfig.bronze_batch("customers") != StorageConfig.bronze(
        "customers"
    )


def test_silver_returns_the_silver_layer_uri() -> None:
    assert StorageConfig.silver("customers") == (
        "s3://mdp-datalake-dev-857854758128/silver/customers"
    )


def test_gold_returns_the_gold_layer_uri() -> None:
    assert StorageConfig.gold("customers") == (
        "s3://mdp-datalake-dev-857854758128/gold/customers"
    )


def test_layer_methods_are_callable_without_instantiation() -> None:
    assert callable(StorageConfig.bronze)
    assert StorageConfig.bronze("orders") != StorageConfig.silver("orders")
