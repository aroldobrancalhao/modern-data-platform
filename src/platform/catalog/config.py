from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class CatalogConfig:
    default_database: str = "default"

    create_if_not_exists: bool = True
