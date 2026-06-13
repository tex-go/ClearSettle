import uuid
from datetime import datetime

from pydantic import BaseModel


class BatchResponse(BaseModel):
    batch_id: uuid.UUID
    file_name: str
    report_type: str
    rows_ingested: int
    uploaded_at: datetime
