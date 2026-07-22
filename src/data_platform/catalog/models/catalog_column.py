from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class CatalogColumn:
    """
    Represents a column definition inside a catalog table.
    """

    name: str

    type: str

    nullable: bool = True

    comment: str | None = None