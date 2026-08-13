from typing import TYPE_CHECKING

from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    # PostgreSQL
    postgres_host: str
    postgres_port: int
    postgres_database: str
    postgres_user: str
    postgres_password: str

    # Simulator
    simulator_batch_size: int = 1000
    simulator_interval_seconds: int = 5
    simulator_insert_batch_size: int = 500
    simulator_restock_probability: float = 0.08

    # Initial Load
    initial_catalog: bool = True

    # Master Data
    sellers_per_batch: int = 10
    categories_per_batch: int = 20
    warehouses_per_batch: int = 5
    products_per_seller: int = 50

    # Transactional Data
    customers_per_batch: int = 1000
    orders_per_batch: int = 1000
    reviews_per_batch: int = 400

    # Orders
    max_order_items: int = 5

    # Inventory
    initial_stock_min: int = 100
    initial_stock_max: int = 1000

    # Features
    enable_payments: bool = True
    enable_shipments: bool = True
    enable_reviews: bool = True

    # Logging
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        case_sensitive=False,
        # extra="ignore": the root .env is shared by more than just
        # this Settings class (e.g. METABASE_ADMIN_EMAIL/PASSWORD,
        # added 2026-08-13 for ad-hoc Metabase API scripts, not a
        # simulator field) -- pydantic-settings' default (extra=
        # "forbid") made any var here that Settings doesn't declare a
        # hard crash for every consumer of this class, discovered live
        # when the simulator failed to start after that addition.
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    if TYPE_CHECKING:
        return Settings(
            postgres_host="",
            postgres_port=5432,
            postgres_database="",
            postgres_user="",
            postgres_password="",
        )

    return Settings()
