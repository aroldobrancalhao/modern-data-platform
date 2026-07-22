from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class DatabricksSettings:
    """
    Databricks SDK configuration.

    Authentication is intentionally delegated to the official
    Databricks SDK credential chain.

    Supported mechanisms include:

    - DATABRICKS_HOST
    - DATABRICKS_TOKEN
    - ~/.databrickscfg
    - Azure CLI
    - Azure Managed Identity
    - OAuth (future)

    This keeps the platform independent from any specific
    authentication mechanism.
    """