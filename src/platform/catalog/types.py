from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class CatalogDatabase:
    name: str

    description: str | None = None


@dataclass(slots=True, frozen=True)
class CatalogTable:
    database: str

    name: str

    location: str
