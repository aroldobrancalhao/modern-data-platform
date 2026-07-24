from datetime import datetime

from pydantic import BaseModel

from data_platform.enums.pipeline_status import PipelineStatus


class ExecutionResult(BaseModel):
    status: PipelineStatus

    started_at: datetime

    finished_at: datetime | None = None

    message: str | None = None