# src/task_api/schemas.py
# Pydantic schemas for Users, Tasks, File Attachments, Tags, Webhooks, Exports, and OpenAPI docs.
# Connects to: src/task_api/models.py, src/task_api/main.py, src/task_api/crud.py, src/task_api/auth.py
# Created: 2026-08-02

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, ConfigDict, HttpUrl
from task_api.models import TaskStatus, TaskPriority


# User Schemas
class UserBase(BaseModel):
    """Base fields shared by User schemas."""
    email: EmailStr = Field(..., description="User email address", json_schema_extra={"example": "user@example.com"})
    full_name: Optional[str] = Field(None, max_length=255, json_schema_extra={"example": "Jane Doe"})


class UserCreate(UserBase):
    """Schema for registering a new user account."""
    password: str = Field(..., min_length=8, max_length=128, description="Account password (min 8 characters)", json_schema_extra={"example": "SecurePass123!"})


class UserResponse(UserBase):
    """Schema for returning user account details."""
    id: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Authentication Token Schemas
class Token(BaseModel):
    """Bearer JWT response schema."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Decoded JWT payload structure."""
    user_id: Optional[int] = None
    email: Optional[str] = None


# Tag Schemas
class TagBase(BaseModel):
    """Base fields for task category tags."""
    name: str = Field(..., min_length=1, max_length=64, description="Tag label name", json_schema_extra={"example": "Work"})
    color: str = Field(default="#6c757d", max_length=32, description="Hex color string", json_schema_extra={"example": "#007bff"})


class TagCreate(TagBase):
    """Schema for creating a tag."""
    pass


class TagResponse(TagBase):
    """Schema for returning tag details."""
    id: int
    owner_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TagListResponse(BaseModel):
    """Container for listing user tags."""
    total: int
    tags: List[TagResponse]


# Attachment Schemas
class AttachmentResponse(BaseModel):
    """Schema for returning file attachment metadata."""
    id: int
    task_id: int
    owner_id: int
    filename: str
    content_type: str
    file_size_bytes: int
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttachmentListResponse(BaseModel):
    """Container for listing attachments linked to a task."""
    total: int
    attachments: List[AttachmentResponse]


# Webhook Schemas
class WebhookBase(BaseModel):
    """Base fields for webhook registration."""
    target_url: HttpUrl = Field(..., description="Target HTTP/HTTPS receiver URL", json_schema_extra={"example": "https://api.example.com/webhook-listener"})


class WebhookCreate(WebhookBase):
    """Schema for registering a webhook listener."""
    secret_token: Optional[str] = Field(None, max_length=128, description="Optional custom secret key for HMAC signing")


class WebhookResponse(WebhookBase):
    """Schema for returning webhook details."""
    id: int
    owner_id: int
    secret_token: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WebhookListResponse(BaseModel):
    """Container for listing user webhooks."""
    total: int
    webhooks: List[WebhookResponse]


# Background Export Schemas
class TaskExportResponse(BaseModel):
    """Schema for returning background task export trigger details."""
    message: str
    filename: str
    total_exported: int


# Task Schemas
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
    owner_id: int
    created_at: datetime
    updated_at: datetime
    tags: List[TagResponse] = []

    model_config = ConfigDict(from_attributes=True)


class TaskListResponse(BaseModel):
    """Paginated or listed response container for tasks."""
    total: int
    tasks: list[TaskResponse]
