"""
Modern Data Platform
Processing Framework

Real-Databricks smoke test for DatabricksComputeProvider.

Confirms the provider resolves through the real bootstrap() ->
ProviderFactory chain and that Databricks authentication actually
works -- without triggering any Job (that costs cluster time/money
and is left for a separate, explicit step once we decide which Job to
run).

Requires valid Databricks credentials and network access, so it is
excluded from the default suite (see
`addopts = -m "not real_aws and not real_databricks"` in
pyproject.toml). Run it explicitly with:

    uv run pytest tests/integration/databricks/test_databricks_provider_real.py -m real_databricks -v

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import pytest

from data_platform.bootstrap import bootstrap
from data_platform.config.settings import Settings
from data_platform.providers.provider_factory import ProviderFactory

from integrations.databricks.compute.databricks_compute_provider import (
    DatabricksComputeProvider,
)
from integrations.databricks.core.databricks_context import (
    DatabricksContext,
)

pytestmark = pytest.mark.real_databricks


def test_bootstrap_resolves_the_real_databricks_compute_provider() -> None:
    factory = ProviderFactory(
        registry=bootstrap(),
        settings=Settings(),
    )

    provider = factory.create("databricks")

    assert isinstance(provider, DatabricksComputeProvider)


def test_databricks_authentication_works_without_triggering_a_job() -> None:
    """
    DatabricksComputeProvider only exposes execute(), which runs a
    real Job -- there is no lighter-weight "check auth" method on the
    provider or its client. DatabricksContext is constructed the same
    way DatabricksComputeBuilder.build() constructs it internally, so
    calling .workspace.current_user.me() here exercises the exact same
    credential resolution path without triggering a Job.
    """

    context = DatabricksContext()

    current_user = context.workspace.current_user.me()

    assert current_user.user_name is not None
