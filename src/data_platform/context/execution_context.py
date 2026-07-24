from pydantic import BaseModel

from data_platform.context.execution_metadata import ExecutionMetadata
from data_platform.enums.environment import Environment
from data_platform.enums.execution_mode import ExecutionMode
from data_platform.enums.execution_source import ExecutionSource


class ExecutionContext(BaseModel):
    metadata: ExecutionMetadata

    environment: Environment

    execution_mode: ExecutionMode

    execution_source: ExecutionSource