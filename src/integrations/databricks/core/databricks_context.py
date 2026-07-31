from functools import cached_property

from databricks.sdk import WorkspaceClient

from integrations.databricks.config.databricks_settings import (
    DatabricksSettings,
)


class DatabricksContext:

    def __init__(
        self,
        settings: DatabricksSettings | None = None,
    ) -> None:
        self._settings = settings or DatabricksSettings()

    @cached_property
    def workspace(self) -> WorkspaceClient:
        return WorkspaceClient(profile=self._settings.profile)

    @cached_property
    def jobs(self) -> dict[str, int]:
        jobs: dict[str, int] = {}

        for job in self.workspace.jobs.list():
            if job.settings is None:
                continue

            if job.job_id is None:
                continue

            if job.settings.name is None:
                continue

            jobs[job.settings.name] = job.job_id

        return jobs

    def resolve_job(self, identifier: str) -> int:
        try:
            return self.jobs[identifier]
        except KeyError as exc:
            raise ValueError(
                f"Databricks Job '{identifier}' was not found."
            ) from exc