# src/task_api/schemas.py
# Pydantic schemas for data validation, serialization, and OpenAPI documentation.
# Connects to: src/task_api/models.py, src/task_api/main.py, src/task_api/crud.py
# Created: 2026-08-02

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from task_api.models import TaskStatus, TaskPriority


class TaskBase(BaseModel):
    """Base fields shared by Task inputs and outputs."""
    title: str = Field(..., min_length=1, max_length=255, description="Task title", json_schema_extra={"example": "Implement OAuth2 Auth"})
    description: Optional[str] = Field(None, max_length=5000, description="Detailed task description", json_schema_extra={"example": "Setup JWT login and registration middleware"})
    status: TaskStatus = Field(default=TaskStatus.TODO, description="Task lifecycle status")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Priority rating")
    due_date: Optional[datetime] = Field(None, description="Optional ISO timestamp due date")


class TaskCreate(TaskBase):
    """Schema for creating a new task."""
    pass


class TaskUpdate(BaseModel):
    """Schema for updating an existing task (partial updates supported)."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None


class TaskResponse(TaskBase):
    """Schema for returning task details in API responses."""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskListResponse(BaseModel):
    """Paginated or listed response container for tasks."""
    total: int
    tasks: list[TaskResponse]
