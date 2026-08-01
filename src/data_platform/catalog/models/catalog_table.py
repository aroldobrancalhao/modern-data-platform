from dataclasses import dataclass, field

from data_platform.catalog.models.catalog_column import CatalogColumn
from data_platform.storage.models import StorageLocation


@dataclass(slots=True, frozen=True)
class CatalogTable:
    """
    Represents a catalog table.
    """

    database: str

    name: str

    location: StorageLocation

    columns: list[CatalogColumn]

    partitions: list[str] = field(default_factory=list)

    description: str | None = None

    table_format: str = "generic"
    """
    The physical file format backing this table -- ``"generic"``
    (plain text/CSV, the historical default) or ``"delta"``.

    A concrete CatalogProvider needs this to know how to register the
    table correctly: a Glue table backed by Delta Lake files requires
    a different InputFormat/OutputFormat/SerDe and table Parameters
    than a plain text table (confirmed empirically against Athena --
    a Delta table registered with the generic format cannot be read
    correctly; `SELECT count(*)` silently returns a wrong number
    instead of erroring). This is a plain ``str``, not an enum/Literal,
    matching how ``CatalogColumn.type`` is already a raw string
    elsewhere in this module -- new formats (e.g. Iceberg) don't
    require changing this dataclass.
    """