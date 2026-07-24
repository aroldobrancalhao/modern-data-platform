from pydantic import BaseModel

from data_platform.enums.pipeline_stage import PipelineStage
from data_platform.enums.pipeline_status import PipelineStatus
from data_platform.datalake.models.dataset import Dataset


class PipelineContext(BaseModel):
    dataset: Dataset

    stage: PipelineStage

    status: PipelineStatus = PipelineStatus.CREATED

    partitions: dict[str, str | int] | None = None