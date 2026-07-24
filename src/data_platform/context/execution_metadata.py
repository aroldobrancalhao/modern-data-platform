from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ExecutionMetadata(BaseModel):
    execution_id: UUID
    correlation_id: UUID
    started_at: datetime