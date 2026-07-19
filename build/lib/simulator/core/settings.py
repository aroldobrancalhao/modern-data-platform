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
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()