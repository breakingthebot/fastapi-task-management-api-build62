# src/task_api/schemas.py
# Pydantic schemas for Users, Tasks, Workspaces, Comments, Attachments, Tags, Webhooks, Activity Logs, Analytics, Exports, and OpenAPI docs.
# Connects to: src/task_api/models.py, src/task_api/main.py, src/task_api/crud.py, src/task_api/auth.py
# Created: 2026-08-02

from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, ConfigDict, HttpUrl
from task_api.models import TaskStatus, TaskPriority, WorkspaceRole


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


# Analytics Schemas
class TaskAnalyticsResponse(BaseModel):
    """Schema for task analytics and productivity dashboard metrics."""
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    completion_rate: float
    tasks_by_priority: Dict[str, int]
    tasks_by_status: Dict[str, int]
    total_attachments: int
    total_comments: int


# Workspace & RBAC Schemas
class WorkspaceBase(BaseModel):
    """Base fields for team workspaces."""
    name: str = Field(..., min_length=1, max_length=128, description="Workspace name", json_schema_extra={"example": "Engineering Team"})
    description: Optional[str] = Field(None, max_length=2000, description="Workspace description", json_schema_extra={"example": "Backend development team workspace"})


class WorkspaceCreate(WorkspaceBase):
    """Schema for creating a workspace."""
    pass


class WorkspaceMemberAdd(BaseModel):
    """Schema for adding a user to a workspace with an assigned RBAC role."""
    user_email: EmailStr = Field(..., description="Email address of user to add")
    role: WorkspaceRole = Field(default=WorkspaceRole.VIEWER, description="Assigned RBAC role (admin, editor, viewer)")


class WorkspaceMemberResponse(BaseModel):
    """Schema for returning workspace membership information."""
    id: int
    workspace_id: int
    user_id: int
    user_email: Optional[str] = None
    role: WorkspaceRole
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkspaceResponse(WorkspaceBase):
    """Schema for returning workspace details."""
    id: int
    owner_id: int
    created_at: datetime
    members: List[WorkspaceMemberResponse] = []

    model_config = ConfigDict(from_attributes=True)


class WorkspaceListResponse(BaseModel):
    """Container for listing user workspaces."""
    total: int
    workspaces: List[WorkspaceResponse]


# Comment Schemas
class CommentBase(BaseModel):
    """Base fields for task comments."""
    content: str = Field(..., min_length=1, max_length=5000, description="Markdown comment text content", json_schema_extra={"example": "I reviewed the PR and tests look solid."})


class CommentCreate(CommentBase):
    """Schema for posting a comment."""
    pass


class CommentUpdate(BaseModel):
    """Schema for editing a comment."""
    content: str = Field(..., min_length=1, max_length=5000)


class CommentResponse(CommentBase):
    """Schema for returning comment details."""
    id: int
    task_id: int
    author_id: int
    author_email: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommentListResponse(BaseModel):
    """Container for listing task comments."""
    total: int
    comments: List[CommentResponse]


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


# Activity Log Schemas
class ActivityLogResponse(BaseModel):
    """Schema for returning task activity audit logs."""
    id: int
    task_id: Optional[int]
    owner_id: int
    action: str
    field_changed: Optional[str]
    old_value: Optional[str]
    new_value: Optional[str]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class ActivityLogListResponse(BaseModel):
    """Container for listing activity logs."""
    total: int
    activities: List[ActivityLogResponse]


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
    workspace_id: Optional[int] = Field(None, description="Optional workspace ID linking task to team workspace")
    parent_id: Optional[int] = Field(None, description="Optional parent task ID for subtask relationships")


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
    parent_id: Optional[int] = None


class TaskResponse(TaskBase):
    """Schema for returning task details in API responses."""
    id: int
    owner_id: int
    workspace_id: Optional[int] = None
    parent_id: Optional[int] = None
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    tags: List[TagResponse] = []

    model_config = ConfigDict(from_attributes=True)


class TaskListResponse(BaseModel):
    """Paginated or listed response container for tasks."""
    total: int
    tasks: list[TaskResponse]
