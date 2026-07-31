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

    ``profile=None`` (the default) means "let the Databricks SDK
    resolve the profile from its own chain" -- the
    ``DATABRICKS_CONFIG_PROFILE`` environment variable, then
    ``default_profile`` in ``~/.databrickscfg``, then the ``DEFAULT``
    profile. Pass an explicit value here only when you need to *force*
    a specific profile regardless of what the environment or the
    local ``~/.databrickscfg`` resolve to (e.g. a machine/CI runner
    whose ``~/.databrickscfg`` has no ``default_profile`` set, or
    doesn't match this project).
    """

    profile: str | None = None