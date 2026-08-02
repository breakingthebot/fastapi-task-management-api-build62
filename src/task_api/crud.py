# src/task_api/crud.py
# Database interaction logic and queries for Task objects.
# Connects to: src/task_api/models.py, src/task_api/schemas.py, src/task_api/database.py
# Created: 2026-08-02

from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from task_api.models import TaskModel, TaskStatus, TaskPriority
from task_api.schemas import TaskCreate, TaskUpdate


def create_task(db: Session, task_in: TaskCreate) -> TaskModel:
    """Create a new task record in the database."""
    db_task = TaskModel(
        title=task_in.title,
        description=task_in.description,
        status=task_in.status,
        priority=task_in.priority,
        due_date=task_in.due_date
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def get_task_by_id(db: Session, task_id: int) -> Optional[TaskModel]:
    """Retrieve a single task by its integer ID."""
    return db.query(TaskModel).filter(TaskModel.id == task_id).first()


def get_tasks(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None,
    search: Optional[str] = None
) -> Tuple[List[TaskModel], int]:
    """Retrieve a list of tasks filtered by status, priority, or search term with pagination."""
    query = db.query(TaskModel)

    if status:
        query = query.filter(TaskModel.status == status)
    if priority:
        query = query.filter(TaskModel.priority == priority)
    if search:
        query = query.filter(TaskModel.title.icontains(search) | TaskModel.description.icontains(search))

    total = query.count()
    tasks = query.order_by(TaskModel.id.desc()).offset(skip).limit(limit).all()
    return tasks, total


def update_task(db: Session, db_task: TaskModel, task_in: TaskUpdate) -> TaskModel:
    """Update an existing task record with non-null input fields."""
    update_data = task_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_task, field, value)

    db.commit()
    db.refresh(db_task)
    return db_task


def delete_task(db: Session, db_task: TaskModel) -> None:
    """Delete a task record from the database."""
    db.delete(db_task)
    db.commit()
