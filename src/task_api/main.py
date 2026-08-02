# src/task_api/main.py
# FastAPI application entry point defining authentication and protected task management endpoints.
# Connects to: src/task_api/config.py, src/task_api/database.py, src/task_api/crud.py, src/task_api/auth.py
# Created: 2026-08-02

from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from task_api import __version__
from task_api.config import settings
from task_api.database import engine, Base, get_db
from task_api.models import TaskStatus, TaskPriority, UserModel
from task_api.schemas import (
    UserCreate, UserResponse, Token,
    TaskCreate, TaskUpdate, TaskResponse, TaskListResponse
)
from task_api import crud
from task_api.auth import verify_password, create_access_token, get_current_user

# Create database tables automatically on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="A robust FastAPI REST service providing JWT authentication and task management lifecycle features.",
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
