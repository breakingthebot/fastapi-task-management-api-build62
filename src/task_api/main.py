# src/task_api/main.py
# FastAPI application entry point defining API routes, OpenAPI documentation, and lifecycle events.
# Connects to: src/task_api/config.py, src/task_api/database.py, src/task_api/crud.py, src/task_api/schemas.py
# Created: 2026-08-02

from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from task_api import __version__
from task_api.config import settings
from task_api.database import engine, Base, get_db
from task_api.models import TaskStatus, TaskPriority
from task_api.schemas import TaskCreate, TaskUpdate, TaskResponse, TaskListResponse
from task_api import crud

# Create database tables automatically on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="A robust FastAPI REST service providing complete task management lifecycle features.",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


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


@app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, tags=["Tasks"], summary="Create a new task")
def create_task_endpoint(task_in: TaskCreate, db: Session = Depends(get_db)):
    """Create a new task with title, description, status, priority, and optional due date."""
    return crud.create_task(db=db, task_in=task_in)


@app.get("/tasks", response_model=TaskListResponse, tags=["Tasks"], summary="List all tasks")
def list_tasks_endpoint(
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Page limit"),
    status: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    priority: Optional[TaskPriority] = Query(None, description="Filter by task priority"),
    search: Optional[str] = Query(None, description="Search keyword in title or description"),
    db: Session = Depends(get_db)
):
    """Retrieve a paginated list of tasks with optional filtering and search parameters."""
    tasks, total = crud.get_tasks(db=db, skip=skip, limit=limit, status=status, priority=priority, search=search)
    return TaskListResponse(total=total, tasks=tasks)


@app.get("/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"], summary="Get task by ID")
def get_task_endpoint(task_id: int, db: Session = Depends(get_db)):
    """Retrieve details for a specific task by its unique ID."""
    db_task = crud.get_task_by_id(db=db, task_id=task_id)
    if not db_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found."
        )
    return db_task


@app.put("/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"], summary="Update task by ID")
def update_task_endpoint(task_id: int, task_in: TaskUpdate, db: Session = Depends(get_db)):
    """Update fields of an existing task by its unique ID."""
    db_task = crud.get_task_by_id(db=db, task_id=task_id)
    if not db_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found."
        )
    return crud.update_task(db=db, db_task=db_task, task_in=task_in)


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Tasks"], summary="Delete task by ID")
def delete_task_endpoint(task_id: int, db: Session = Depends(get_db)):
    """Remove a task record by its unique ID."""
    db_task = crud.get_task_by_id(db=db, task_id=task_id)
    if not db_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found."
        )
    crud.delete_task(db=db, db_task=db_task)
    return None
