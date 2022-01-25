# generated by datamodel-codegen:
#   filename:  task_log_request.json

from __future__ import annotations

from pydantic import BaseModel, Field


class TaskLogRequest(BaseModel):
    type: str = Field(..., description="Indicate that this is a task log request")
    task_id: str = Field(
        ..., description="Specify the ID of the task whose log should be fetched"
    )
