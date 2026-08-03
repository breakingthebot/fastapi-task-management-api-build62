# src/task_api/main.py
# FastAPI application entry point defining auth, tasks, attachments, tags, webhooks, activity logs, workspaces, comments, analytics, rate limiting, caching, and background tasks.
# Connects to: src/task_api/config.py, src/task_api/database.py, src/task_api/crud.py, src/task_api/auth.py, src/task_api/services.py, src/task_api/cache.py, src/task_api/rate_limiter.py
# Created: 2026-08-02

import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File, BackgroundTasks, Response, Request, status
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from task_api import __version__
from task_api.config import settings
from task_api.database import engine, Base, get_db
from task_api.models import TaskStatus, TaskPriority, WorkspaceRole, UserModel
from task_api.schemas import (
    UserCreate, UserResponse, Token,
    TaskCreate, TaskUpdate, TaskResponse, TaskListResponse,
    AttachmentResponse, AttachmentListResponse, TaskExportResponse,
    TagCreate, TagResponse, TagListResponse,
    WebhookCreate, WebhookResponse, WebhookListResponse,
    ActivityLogResponse, ActivityLogListResponse,
    WorkspaceCreate, WorkspaceResponse, WorkspaceListResponse,
    WorkspaceMemberAdd, WorkspaceMemberResponse,
    CommentCreate, CommentResponse, CommentListResponse,
    TaskAnalyticsResponse
)
from task_api import crud
from task_api.auth import verify_password, create_access_token, get_current_user
from task_api.services import send_urgent_task_notification, generate_task_csv_export, dispatch_webhook_event
from task_api.cache import cache_service
from task_api.rate_limiter import rate_limiter

# Create database tables automatically on startup
Base.metadata.create_all(bind=engine)

# Ensure upload & export directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
EXPORT_DIR = os.path.join(settings.UPLOAD_DIR, "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)

app = FastAPI(
    title=settings.APP_NAME,
    description="A robust FastAPI REST service providing JWT auth, task CRUD, team workspaces, RBAC roles, analytics dashboard, discussion comments, rate limiting, attachments, tags, webhooks, audit logs, caching, and background tasks.",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# Rate Limiting Middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Enforce sliding-window request throttling per client IP address."""
    client_ip = request.client.host if request.client else "127.0.0.1"

    # Strict limit on login requests (5 per 60 seconds)
    if request.url.path == "/auth/login" and request.method == "POST":
        allowed, retry_after = rate_limiter.check_rate_limit(f"login:{client_ip}", max_requests=5, window_seconds=60)
        if not allowed:
            return Response(
                content='{"detail": "Too many login attempts. Please try again later."}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(retry_after), "Content-Type": "application/json"}
            )
    else:
        # General limit on all other endpoints (1000 per 60 seconds)
        allowed, retry_after = rate_limiter.check_rate_limit(f"general:{client_ip}", max_requests=1000, window_seconds=60)
        if not allowed:
            return Response(
                content='{"detail": "Rate limit exceeded. Please try again later."}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(retry_after), "Content-Type": "application/json"}
            )

    response = await call_next(request)
    return response


# System & Health Endpoints
@app.get("/health", tags=["System"], summary="Health check endpoint")
def health_check():
    """Return health status and API version information."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": __version__,
        "environment": settings.APP_ENV
    }


@app.get("/version", tags=["System"], summary="API version endpoint")
def version_endpoint():
    """Return current API version string."""
    return {"version": __version__}


# Analytics Endpoint
@app.get("/analytics/tasks", response_model=TaskAnalyticsResponse, tags=["Analytics"], summary="Get task analytics and productivity dashboard metrics")
def get_task_analytics_endpoint(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Retrieve aggregated task counts, completion rates, priority distributions, and activity statistics."""
    analytics = crud.get_task_analytics(db=db, owner_id=current_user.id)
    return TaskAnalyticsResponse(**analytics)


# Authentication Endpoints
@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Authentication"], summary="Register a new user account")
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new user account with unique email and hashed password."""
    existing_user = crud.get_user_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )
    return crud.create_user(db=db, user_in=user_in)


@app.post("/auth/login", response_model=Token, tags=["Authentication"], summary="Obtain JWT access token")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Authenticate email & password credentials to receive a Bearer JWT access token."""
    user = crud.get_user_by_email(db, email=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user account.")

    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    return Token(access_token=access_token, token_type="bearer")


@app.get("/auth/me", response_model=UserResponse, tags=["Authentication"], summary="Get current user profile")
def get_current_user_profile(current_user: UserModel = Depends(get_current_user)):
    """Retrieve details for the currently authenticated user."""
    return current_user


# Workspace & RBAC Endpoints
@app.post("/workspaces", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED, tags=["Workspaces & RBAC"], summary="Create team workspace")
def create_workspace_endpoint(
    workspace_in: WorkspaceCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Create a new team workspace and assign ADMIN role to creator."""
    return crud.create_workspace(db=db, workspace_in=workspace_in, owner_id=current_user.id)


@app.get("/workspaces", response_model=WorkspaceListResponse, tags=["Workspaces & RBAC"], summary="List user workspaces")
def list_workspaces_endpoint(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Retrieve all workspaces where the current user is a member."""
    workspaces = crud.get_user_workspaces(db=db, user_id=current_user.id)
    return WorkspaceListResponse(total=len(workspaces), workspaces=workspaces)


@app.post("/workspaces/{workspace_id}/members", response_model=WorkspaceMemberResponse, status_code=status.HTTP_201_CREATED, tags=["Workspaces & RBAC"], summary="Add member to workspace (Admin Only)")
def add_workspace_member_endpoint(
    workspace_id: int,
    member_in: WorkspaceMemberAdd,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Add a user to a workspace with an assigned RBAC role (Admin, Editor, Viewer)."""
    role = crud.get_workspace_member_role(db=db, workspace_id=workspace_id, user_id=current_user.id)
    if role != WorkspaceRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workspace Admins can manage members."
        )

    target_user = crud.get_user_by_email(db=db, email=member_in.user_email)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with email '{member_in.user_email}' not found.")

    member = crud.add_workspace_member(db=db, workspace_id=workspace_id, user_id=target_user.id, role=member_in.role)
    return WorkspaceMemberResponse(
        id=member.id,
        workspace_id=member.workspace_id,
        user_id=member.user_id,
        user_email=target_user.email,
        role=member.role,
        joined_at=member.joined_at
    )


@app.delete("/workspaces/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Workspaces & RBAC"], summary="Remove member from workspace (Admin Only)")
def remove_workspace_member_endpoint(
    workspace_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Remove a user membership from a workspace."""
    role = crud.get_workspace_member_role(db=db, workspace_id=workspace_id, user_id=current_user.id)
    if role != WorkspaceRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only workspace Admins can manage members.")

    member = crud.get_workspace_member(db=db, workspace_id=workspace_id, user_id=user_id)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User ID {user_id} is not a member of workspace {workspace_id}.")

    crud.remove_workspace_member(db=db, member=member)
    return None


# Comment Endpoints
@app.post("/tasks/{task_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED, tags=["Comments"], summary="Post a comment on a task")
def create_comment_endpoint(
    task_id: int,
    comment_in: CommentCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Post a discussion comment on a task."""
    db_task = crud.get_task_by_id(db=db, task_id=task_id, owner_id=current_user.id)
    if not db_task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with ID {task_id} not found.")

    db_comment = crud.create_comment(db=db, task_id=task_id, author_id=current_user.id, comment_in=comment_in)

    crud.create_activity_log(
        db=db,
        task_id=task_id,
        owner_id=current_user.id,
        action="comment.created",
        new_value=db_comment.content[:100]
    )

    return CommentResponse(
        id=db_comment.id,
        task_id=db_comment.task_id,
        author_id=db_comment.author_id,
        author_email=current_user.email,
        content=db_comment.content,
        created_at=db_comment.created_at,
        updated_at=db_comment.updated_at
    )


@app.get("/tasks/{task_id}/comments", response_model=CommentListResponse, tags=["Comments"], summary="List task comments")
def list_task_comments_endpoint(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """List all discussion comments posted on a task."""
    db_task = crud.get_task_by_id(db=db, task_id=task_id, owner_id=current_user.id)
    if not db_task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with ID {task_id} not found.")

    comments = crud.get_task_comments(db=db, task_id=task_id)
    comment_responses = []
    for c in comments:
        author = crud.get_user_by_id(db=db, user_id=c.author_id)
        comment_responses.append(CommentResponse(
            id=c.id,
            task_id=c.task_id,
            author_id=c.author_id,
            author_email=author.email if author else None,
            content=c.content,
            created_at=c.created_at,
            updated_at=c.updated_at
        ))

    return CommentListResponse(total=len(comment_responses), comments=comment_responses)


@app.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Comments"], summary="Delete comment by ID")
def delete_comment_endpoint(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Delete a comment by ID (Author or Workspace Admin)."""
    db_comment = crud.get_comment_by_id(db=db, comment_id=comment_id)
    if not db_comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Comment with ID {comment_id} not found.")

    db_task = crud.get_task_by_id(db=db, task_id=db_comment.task_id, owner_id=current_user.id)
    if not db_task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    is_author = (db_comment.author_id == current_user.id)
    is_admin = False
    if db_task.workspace_id:
        role = crud.get_workspace_member_role(db=db, workspace_id=db_task.workspace_id, user_id=current_user.id)
        is_admin = (role == WorkspaceRole.ADMIN)

    if not (is_author or is_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only comment author or workspace Admin can delete this comment.")

    crud.delete_comment(db=db, db_comment=db_comment)
    return None


# Activity Audit Log Endpoints
@app.get("/activity", response_model=ActivityLogListResponse, tags=["Activity Audit"], summary="Get overall activity audit trail")
def list_user_activity_logs_endpoint(
    limit: int = Query(50, ge=1, le=200, description="Max audit entries"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Retrieve user-wide activity audit logs."""
    logs = crud.get_activity_logs_by_user(db=db, owner_id=current_user.id, limit=limit)
    return ActivityLogListResponse(total=len(logs), activities=logs)


@app.get("/tasks/{task_id}/activity", response_model=ActivityLogListResponse, tags=["Activity Audit"], summary="Get activity audit log for a task")
def list_task_activity_logs_endpoint(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Retrieve activity audit log history for a specific task."""
    db_task = crud.get_task_by_id(db=db, task_id=task_id, owner_id=current_user.id)
    if not db_task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with ID {task_id} not found.")

    logs = crud.get_activity_logs_by_task(db=db, task_id=task_id, owner_id=current_user.id)
    return ActivityLogListResponse(total=len(logs), activities=logs)


# Webhook Management Endpoints
@app.post("/webhooks", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED, tags=["Webhooks"], summary="Register a webhook URL")
def register_webhook_endpoint(
    webhook_in: WebhookCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Register an HTTP receiver URL to receive HMAC-signed event notifications."""
    return crud.create_webhook(db=db, webhook_in=webhook_in, owner_id=current_user.id)


@app.get("/webhooks", response_model=WebhookListResponse, tags=["Webhooks"], summary="List registered webhooks")
def list_webhooks_endpoint(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """List all active webhook URLs registered by the current user."""
    webhooks = crud.get_webhooks_by_user(db=db, owner_id=current_user.id)
    return WebhookListResponse(total=len(webhooks), webhooks=webhooks)


@app.delete("/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Webhooks"], summary="Delete webhook registration")
def delete_webhook_endpoint(
    webhook_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Unregister a webhook URL by ID."""
    db_webhook = crud.get_webhook_by_id(db=db, webhook_id=webhook_id, owner_id=current_user.id)
    if not db_webhook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Webhook with ID {webhook_id} not found.")
    crud.delete_webhook(db=db, db_webhook=db_webhook)
    return None


# Tag Management Endpoints
@app.post("/tags", response_model=TagResponse, status_code=status.HTTP_201_CREATED, tags=["Tags"], summary="Create a new tag")
def create_tag_endpoint(
    tag_in: TagCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Create a new task category tag for the current user."""
    existing_tag = crud.get_tag_by_name(db=db, name=tag_in.name, owner_id=current_user.id)
    if existing_tag:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A tag named '{tag_in.name}' already exists."
        )
    return crud.create_tag(db=db, tag_in=tag_in, owner_id=current_user.id)


@app.get("/tags", response_model=TagListResponse, tags=["Tags"], summary="List all tags for current user")
def list_tags_endpoint(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Retrieve all category tags owned by the current user."""
    tags = crud.get_tags(db=db, owner_id=current_user.id)
    return TagListResponse(total=len(tags), tags=tags)


# Protected Task Endpoints
@app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, tags=["Tasks"], summary="Create a new task")
def create_task_endpoint(
    task_in: TaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Create a new task owned by user or in a workspace with Admin/Editor permission."""
    if task_in.workspace_id:
        role = crud.get_workspace_member_role(db=db, workspace_id=task_in.workspace_id, user_id=current_user.id)
        if role not in (WorkspaceRole.ADMIN, WorkspaceRole.EDITOR):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Viewer role cannot create tasks in workspace."
            )

    db_task = crud.create_task(db=db, task_in=task_in, owner_id=current_user.id)
    cache_service.invalidate_user_cache(current_user.id)

    crud.create_activity_log(
        db=db,
        task_id=db_task.id,
        owner_id=current_user.id,
        action="task.created",
        new_value=db_task.title
    )

    if db_task.priority in (TaskPriority.HIGH, TaskPriority.URGENT):
        background_tasks.add_task(
            send_urgent_task_notification,
            user_email=current_user.email,
            task_title=db_task.title,
            task_priority=db_task.priority.value
        )

    task_data = {"id": db_task.id, "title": db_task.title, "status": db_task.status.value, "priority": db_task.priority.value}
    background_tasks.add_task(dispatch_webhook_event, "task.created", task_data, current_user.id)

    return db_task


@app.get("/tasks", tags=["Tasks"], summary="List all tasks for current user (Cached)")
def list_tasks_endpoint(
    response: Response,
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Page limit"),
    status: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    priority: Optional[TaskPriority] = Query(None, description="Filter by task priority"),
    search: Optional[str] = Query(None, description="Search keyword in title or description"),
    tag: Optional[str] = Query(None, description="Filter by tag name"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Retrieve a paginated list of tasks owned by user or shared in workspaces with response caching."""
    cache_key = f"tasks:user:{current_user.id}:list:{skip}_{limit}_{status}_{priority}_{search}_{tag}"
    cached_payload = cache_service.get(cache_key)

    if cached_payload is not None:
        response.headers["X-Cache"] = "HIT"
        return cached_payload

    tasks, total = crud.get_tasks(
        db=db,
        owner_id=current_user.id,
        skip=skip,
        limit=limit,
        status=status,
        priority=priority,
        search=search,
        tag=tag
    )

    res_data = TaskListResponse(total=total, tasks=tasks).model_dump(mode="json")
    cache_service.set(cache_key, res_data, ttl_seconds=60)

    response.headers["X-Cache"] = "MISS"
    return res_data


@app.get("/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"], summary="Get task by ID")
def get_task_endpoint(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Retrieve details for a specific task owned by user or in shared workspace."""
    db_task = crud.get_task_by_id(db=db, task_id=task_id, owner_id=current_user.id)
    if not db_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found."
        )
    return db_task


@app.put("/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"], summary="Update task by ID")
def update_task_endpoint(
    task_id: int,
    task_in: TaskUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Update fields of an existing task (Requires Admin/Editor in workspace)."""
    db_task = crud.get_task_by_id(db=db, task_id=task_id, owner_id=current_user.id)
    if not db_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found."
        )

    if db_task.workspace_id and db_task.owner_id != current_user.id:
        role = crud.get_workspace_member_role(db=db, workspace_id=db_task.workspace_id, user_id=current_user.id)
        if role not in (WorkspaceRole.ADMIN, WorkspaceRole.EDITOR):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Viewer role cannot update workspace tasks.")

    update_dict = task_in.model_dump(exclude_unset=True)
    for field, new_val in update_dict.items():
        old_val = getattr(db_task, field)
        if old_val != new_val:
            crud.create_activity_log(
                db=db,
                task_id=db_task.id,
                owner_id=current_user.id,
                action="task.updated",
                field_changed=field,
                old_value=str(old_val),
                new_value=str(new_val)
            )

    updated_task = crud.update_task(db=db, db_task=db_task, task_in=task_in)
    cache_service.invalidate_user_cache(current_user.id)

    task_data = {"id": updated_task.id, "title": updated_task.title, "status": updated_task.status.value, "priority": updated_task.priority.value}
    background_tasks.add_task(dispatch_webhook_event, "task.updated", task_data, current_user.id)

    return updated_task


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Tasks"], summary="Delete task by ID")
def delete_task_endpoint(
    task_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Remove a task record (Requires Owner or Admin in workspace)."""
    db_task = crud.get_task_by_id(db=db, task_id=task_id, owner_id=current_user.id)
    if not db_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found."
        )

    if db_task.workspace_id and db_task.owner_id != current_user.id:
        role = crud.get_workspace_member_role(db=db, workspace_id=db_task.workspace_id, user_id=current_user.id)
        if role != WorkspaceRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Task Owner or Workspace Admin can delete workspace tasks.")

    deleted_id = db_task.id
    task_title = db_task.title
    crud.delete_task(db=db, db_task=db_task)
    cache_service.invalidate_user_cache(current_user.id)

    crud.create_activity_log(
        db=db,
        task_id=None,
        owner_id=current_user.id,
        action="task.deleted",
        old_value=task_title
    )

    background_tasks.add_task(dispatch_webhook_event, "task.deleted", {"id": deleted_id}, current_user.id)

    return None


@app.post("/tasks/{task_id}/tags/{tag_id}", response_model=TaskResponse, tags=["Tags"], summary="Attach tag to task")
def attach_tag_to_task_endpoint(
    task_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Associate a tag with a task owned by the current user."""
    db_task = crud.get_task_by_id(db=db, task_id=task_id, owner_id=current_user.id)
    if not db_task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with ID {task_id} not found.")

    db_tag = crud.get_tag_by_id(db=db, tag_id=tag_id, owner_id=current_user.id)
    if not db_tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tag with ID {tag_id} not found.")

    updated_task = crud.add_tag_to_task(db=db, db_task=db_task, db_tag=db_tag)
    cache_service.invalidate_user_cache(current_user.id)

    crud.create_activity_log(
        db=db,
        task_id=task_id,
        owner_id=current_user.id,
        action="tag.attached",
        new_value=db_tag.name
    )

    return updated_task


@app.delete("/tasks/{task_id}/tags/{tag_id}", response_model=TaskResponse, tags=["Tags"], summary="Remove tag from task")
def remove_tag_from_task_endpoint(
    task_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Remove a tag association from a task owned by the current user."""
    db_task = crud.get_task_by_id(db=db, task_id=task_id, owner_id=current_user.id)
    if not db_task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with ID {task_id} not found.")

    db_tag = crud.get_tag_by_id(db=db, tag_id=tag_id, owner_id=current_user.id)
    if not db_tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tag with ID {tag_id} not found.")

    updated_task = crud.remove_tag_from_task(db=db, db_task=db_task, db_tag=db_tag)
    cache_service.invalidate_user_cache(current_user.id)

    crud.create_activity_log(
        db=db,
        task_id=task_id,
        owner_id=current_user.id,
        action="tag.removed",
        old_value=db_tag.name
    )

    return updated_task


# Protected File Attachment Endpoints
@app.post("/tasks/{task_id}/attachments", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED, tags=["Attachments"], summary="Upload task file attachment")
def upload_attachment_endpoint(
    task_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Upload a document or image attachment to a task owned by the current user."""
    db_task = crud.get_task_by_id(db=db, task_id=task_id, owner_id=current_user.id)
    if not db_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found."
        )

    file_bytes = file.file.read()
    file_size = len(file_bytes)

    if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size ({file_size} bytes) exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_BYTES} bytes."
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot upload an empty file."
        )

    file_ext = Path(file.filename).suffix
    unique_name = f"{uuid.uuid4().hex}{file_ext}"
    stored_path = os.path.join(settings.UPLOAD_DIR, unique_name)

    with open(stored_path, "wb") as f:
        f.write(file_bytes)

    attachment = crud.create_attachment(
        db=db,
        task_id=task_id,
        owner_id=current_user.id,
        filename=file.filename,
        stored_filename=unique_name,
        file_path=stored_path,
        content_type=file.content_type or "application/octet-stream",
        file_size_bytes=file_size
    )

    crud.create_activity_log(
        db=db,
        task_id=task_id,
        owner_id=current_user.id,
        action="attachment.uploaded",
        new_value=file.filename
    )

    return attachment


@app.get("/tasks/{task_id}/attachments", response_model=AttachmentListResponse, tags=["Attachments"], summary="List task attachments")
def list_task_attachments_endpoint(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Retrieve metadata for all attachments linked to a task owned by the current user."""
    db_task = crud.get_task_by_id(db=db, task_id=task_id, owner_id=current_user.id)
    if not db_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found."
        )
    attachments = crud.get_attachments_by_task(db=db, task_id=task_id, owner_id=current_user.id)
    return AttachmentListResponse(total=len(attachments), attachments=attachments)


@app.get("/attachments/{attachment_id}/download", tags=["Attachments"], summary="Download file attachment")
def download_attachment_endpoint(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Download an uploaded file attachment owned by the current user."""
    attachment = crud.get_attachment_by_id_and_owner(db=db, attachment_id=attachment_id, owner_id=current_user.id)
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attachment with ID {attachment_id} not found."
        )

    if not os.path.exists(attachment.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File content does not exist on disk."
        )

    return FileResponse(
        path=attachment.file_path,
        filename=attachment.filename,
        media_type=attachment.content_type
    )


@app.delete("/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Attachments"], summary="Delete file attachment")
def delete_attachment_endpoint(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Delete an attachment record and remove the associated file from disk."""
    attachment = crud.get_attachment_by_id_and_owner(db=db, attachment_id=attachment_id, owner_id=current_user.id)
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attachment with ID {attachment_id} not found."
        )

    filename = attachment.filename
    task_id = attachment.task_id

    if os.path.exists(attachment.file_path):
        os.remove(attachment.file_path)

    crud.delete_attachment(db=db, db_attachment=attachment)

    crud.create_activity_log(
        db=db,
        task_id=task_id,
        owner_id=current_user.id,
        action="attachment.deleted",
        old_value=filename
    )

    return None


# Background Processing & Export Endpoints
@app.post("/tasks/export", response_model=TaskExportResponse, status_code=status.HTTP_202_ACCEPTED, tags=["Background Tasks"], summary="Export user tasks to CSV (Background Task)")
def export_tasks_background_endpoint(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Trigger an asynchronous background task to export all tasks owned by the current user into a CSV file."""
    tasks, total = crud.get_tasks(db=db, owner_id=current_user.id, limit=1000)

    tasks_data = [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "status": t.status.value,
            "priority": t.priority.value,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None
        }
        for t in tasks
    ]

    filename = f"export_user_{current_user.id}_{uuid.uuid4().hex[:8]}.csv"
    export_filepath = os.path.join(EXPORT_DIR, filename)

    background_tasks.add_task(
        generate_task_csv_export,
        export_filepath=export_filepath,
        user_email=current_user.email,
        tasks_data=tasks_data
    )

    return TaskExportResponse(
        message="CSV export processing enqueued successfully in background.",
        filename=filename,
        total_exported=total
    )


@app.get("/exports/{filename}/download", tags=["Background Tasks"], summary="Download generated task export CSV")
def download_export_file_endpoint(
    filename: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Download a generated task CSV export file."""
    safe_filename = Path(filename).name
    if not safe_filename.startswith(f"export_user_{current_user.id}_"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export file not found or unauthorized."
        )

    filepath = os.path.join(EXPORT_DIR, safe_filename)
    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export file is still processing or does not exist."
        )

    return FileResponse(
        path=filepath,
        filename=safe_filename,
        media_type="text/csv"
    )
