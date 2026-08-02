# src/task_api/crud.py
# Database interaction logic and queries for User and Task objects.
# Connects to: src/task_api/models.py, src/task_api/schemas.py, src/task_api/auth.py
# Created: 2026-08-02

from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from task_api.models import UserModel, TaskModel, TaskStatus, TaskPriority
from task_api.schemas import UserCreate, TaskCreate, TaskUpdate
from task_api.auth import get_password_hash


# User CRUD Operations
def create_user(db: Session, user_in: UserCreate) -> UserModel:
    """Hash password and persist a new UserModel account."""
    hashed_pwd = get_password_hash(user_in.password)
    db_user = UserModel(
        email=user_in.email.lower(),
        hashed_password=hashed_pwd,
        full_name=user_in.full_name,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_email(db: Session, email: str) -> Optional[UserModel]:
    """Retrieve a user account by email address."""
    return db.query(UserModel).filter(UserModel.email == email.lower()).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[UserModel]:
    """Retrieve a user account by unique integer ID."""
    return db.query(UserModel).filter(UserModel.id == user_id).first()


# Task CRUD Operations (User-Scoped)
def create_task(db: Session, task_in: TaskCreate, owner_id: int) -> TaskModel:
    """Create a new task record linked to an authenticated owner_id."""
    db_task = TaskModel(
        title=task_in.title,
        description=task_in.description,
        status=task_in.status,
        priority=task_in.priority,
        due_date=task_in.due_date,
        owner_id=owner_id
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def get_task_by_id(db: Session, task_id: int, owner_id: int) -> Optional[TaskModel]:
    """Retrieve a single task owned by the specified user_id."""
    return db.query(TaskModel).filter(TaskModel.id == task_id, TaskModel.owner_id == owner_id).first()


def get_tasks(
    db: Session,
    owner_id: int,
    skip: int = 0,
    limit: int = 50,
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None,
    search: Optional[str] = None
) -> Tuple[List[TaskModel], int]:
    """Retrieve a paginated list of tasks belonging to owner_id with optional filters."""
    query = db.query(TaskModel).filter(TaskModel.owner_id == owner_id)

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
