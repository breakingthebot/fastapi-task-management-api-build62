# src/task_api/main.py
# FastAPI application entry point defining authentication, protected task management, and file attachment endpoints.
# Connects to: src/task_api/config.py, src/task_api/database.py, src/task_api/crud.py, src/task_api/auth.py
# Created: 2026-08-02

import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from task_api import __version__
from task_api.config import settings
from task_api.database import engine, Base, get_db
from task_api.models import TaskStatus, TaskPriority, UserModel
from task_api.schemas import (
    UserCreate, UserResponse, Token,
    TaskCreate, TaskUpdate, TaskResponse, TaskListResponse,
    AttachmentResponse, AttachmentListResponse
)
from task_api import crud
from task_api.auth import verify_password, create_access_token, get_current_user

# Create database tables automatically on startup
Base.metadata.create_all(bind=engine)

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title=settings.APP_NAME,
    description="A robust FastAPI REST service providing JWT authentication, task CRUD operations, and file attachments.",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


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


# Protected Task Endpoints
@app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, tags=["Tasks"], summary="Create a new task")
def create_task_endpoint(
    task_in: TaskCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Create a new task owned by the current authenticated user."""
    return crud.create_task(db=db, task_in=task_in, owner_id=current_user.id)


@app.get("/tasks", response_model=TaskListResponse, tags=["Tasks"], summary="List all tasks for current user")
def list_tasks_endpoint(
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Page limit"),
    status: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    priority: Optional[TaskPriority] = Query(None, description="Filter by task priority"),
    search: Optional[str] = Query(None, description="Search keyword in title or description"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Retrieve a paginated list of tasks owned by the current user."""
    tasks, total = crud.get_tasks(
        db=db,
        owner_id=current_user.id,
        skip=skip,
        limit=limit,
        status=status,
        priority=priority,
        search=search
    )
    return TaskListResponse(total=total, tasks=tasks)


@app.get("/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"], summary="Get task by ID")
def get_task_endpoint(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Retrieve details for a specific task owned by the current user."""
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
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Update fields of an existing task owned by the current user."""
    db_task = crud.get_task_by_id(db=db, task_id=task_id, owner_id=current_user.id)
    if not db_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found."
        )
    return crud.update_task(db=db, db_task=db_task, task_in=task_in)


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Tasks"], summary="Delete task by ID")
def delete_task_endpoint(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Remove a task record owned by the current user."""
    db_task = crud.get_task_by_id(db=db, task_id=task_id, owner_id=current_user.id)
    if not db_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found."
        )
    crud.delete_task(db=db, db_task=db_task)
    return None


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

    # Read and validate file size
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

    # Generate unique stored filename to prevent collisions and path traversal
    file_ext = Path(file.filename).suffix
    unique_name = f"{uuid.uuid4().hex}{file_ext}"
    stored_path = os.path.join(settings.UPLOAD_DIR, unique_name)

    # Save file content to disk
    with open(stored_path, "wb") as f:
        f.write(file_bytes)

    # Save database attachment record
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

    # Remove file from disk if present
    if os.path.exists(attachment.file_path):
        os.remove(attachment.file_path)

    crud.delete_attachment(db=db, db_attachment=attachment)
    return None
