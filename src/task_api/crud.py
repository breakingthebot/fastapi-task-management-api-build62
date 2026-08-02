# src/task_api/crud.py
# Database interaction logic and queries for User, Task, Attachment, Tag, Webhook, and ActivityLog objects.
# Connects to: src/task_api/models.py, src/task_api/schemas.py, src/task_api/auth.py
# Created: 2026-08-02

import secrets
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from task_api.models import UserModel, TaskModel, AttachmentModel, TagModel, WebhookModel, ActivityLogModel, TaskStatus, TaskPriority
from task_api.schemas import UserCreate, TaskCreate, TaskUpdate, TagCreate, WebhookCreate
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


# Activity Log CRUD Operations
def create_activity_log(
    db: Session,
    owner_id: int,
    action: str,
    task_id: Optional[int] = None,
    field_changed: Optional[str] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None
) -> ActivityLogModel:
    """Record an immutable activity audit log entry."""
    log_entry = ActivityLogModel(
        task_id=task_id,
        owner_id=owner_id,
        action=action,
        field_changed=field_changed,
        old_value=str(old_value) if old_value is not None else None,
        new_value=str(new_value) if new_value is not None else None
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry


def get_activity_logs_by_task(db: Session, task_id: int, owner_id: int) -> List[ActivityLogModel]:
    """Retrieve activity audit trail entries for a specific task."""
    return db.query(ActivityLogModel).filter(
        ActivityLogModel.task_id == task_id,
        ActivityLogModel.owner_id == owner_id
    ).order_by(ActivityLogModel.id.desc()).all()


def get_activity_logs_by_user(db: Session, owner_id: int, limit: int = 100) -> List[ActivityLogModel]:
    """Retrieve overall activity audit trail entries for a user."""
    return db.query(ActivityLogModel).filter(
        ActivityLogModel.owner_id == owner_id
    ).order_by(ActivityLogModel.id.desc()).limit(limit).all()


# Webhook CRUD Operations
def create_webhook(db: Session, webhook_in: WebhookCreate, owner_id: int) -> WebhookModel:
    """Register a new webhook URL with auto-generated or custom HMAC secret token."""
    secret = webhook_in.secret_token or secrets.token_hex(24)
    db_webhook = WebhookModel(
        target_url=str(webhook_in.target_url),
        secret_token=secret,
        owner_id=owner_id,
        is_active=True
    )
    db.add(db_webhook)
    db.commit()
    db.refresh(db_webhook)
    return db_webhook


def get_webhooks_by_user(db: Session, owner_id: int) -> List[WebhookModel]:
    """Retrieve all active webhooks registered by a user."""
    return db.query(WebhookModel).filter(
        WebhookModel.owner_id == owner_id,
        WebhookModel.is_active == True
    ).all()


def get_webhook_by_id(db: Session, webhook_id: int, owner_id: int) -> Optional[WebhookModel]:
    """Retrieve a single webhook record by ID owned by user."""
    return db.query(WebhookModel).filter(
        WebhookModel.id == webhook_id,
        WebhookModel.owner_id == owner_id
    ).first()


def delete_webhook(db: Session, db_webhook: WebhookModel) -> None:
    """Delete a webhook record."""
    db.delete(db_webhook)
    db.commit()


# Tag CRUD Operations
def create_tag(db: Session, tag_in: TagCreate, owner_id: int) -> TagModel:
    """Create a new tag entity for a user."""
    db_tag = TagModel(
        name=tag_in.name,
        color=tag_in.color,
        owner_id=owner_id
    )
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    return db_tag


def get_tags(db: Session, owner_id: int) -> List[TagModel]:
    """Retrieve all tags owned by a user."""
    return db.query(TagModel).filter(TagModel.owner_id == owner_id).all()


def get_tag_by_id(db: Session, tag_id: int, owner_id: int) -> Optional[TagModel]:
    """Retrieve a single tag by ID owned by user."""
    return db.query(TagModel).filter(TagModel.id == tag_id, TagModel.owner_id == owner_id).first()


def get_tag_by_name(db: Session, name: str, owner_id: int) -> Optional[TagModel]:
    """Retrieve tag by name owned by user."""
    return db.query(TagModel).filter(TagModel.name.ilike(name), TagModel.owner_id == owner_id).first()


def add_tag_to_task(db: Session, db_task: TaskModel, db_tag: TagModel) -> TaskModel:
    """Link a tag to a task if not already associated."""
    if db_tag not in db_task.tags:
        db_task.tags.append(db_tag)
        db.commit()
        db.refresh(db_task)
    return db_task


def remove_tag_from_task(db: Session, db_task: TaskModel, db_tag: TagModel) -> TaskModel:
    """Remove a tag link from a task."""
    if db_tag in db_task.tags:
        db_task.tags.remove(db_tag)
        db.commit()
        db.refresh(db_task)
    return db_task


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
    search: Optional[str] = None,
    tag: Optional[str] = None
) -> Tuple[List[TaskModel], int]:
    """Retrieve a paginated list of tasks belonging to owner_id with optional filters including tag name."""
    query = db.query(TaskModel).filter(TaskModel.owner_id == owner_id)

    if status:
        query = query.filter(TaskModel.status == status)
    if priority:
        query = query.filter(TaskModel.priority == priority)
    if search:
        query = query.filter(TaskModel.title.icontains(search) | TaskModel.description.icontains(search))
    if tag:
        query = query.join(TaskModel.tags).filter(TagModel.name.ilike(tag))

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


# Attachment CRUD Operations
def create_attachment(
    db: Session,
    task_id: int,
    owner_id: int,
    filename: str,
    stored_filename: str,
    file_path: str,
    content_type: str,
    file_size_bytes: int
) -> AttachmentModel:
    """Persist file attachment metadata in the database."""
    db_attachment = AttachmentModel(
        task_id=task_id,
        owner_id=owner_id,
        filename=filename,
        stored_filename=stored_filename,
        file_path=file_path,
        content_type=content_type,
        file_size_bytes=file_size_bytes
    )
    db.add(db_attachment)
    db.commit()
    db.refresh(db_attachment)
    return db_attachment


def get_attachments_by_task(db: Session, task_id: int, owner_id: int) -> List[AttachmentModel]:
    """List all attachments linked to a task owned by owner_id."""
    return db.query(AttachmentModel).filter(
        AttachmentModel.task_id == task_id,
        AttachmentModel.owner_id == owner_id
    ).all()


def get_attachment_by_id_and_owner(db: Session, attachment_id: int, owner_id: int) -> Optional[AttachmentModel]:
    """Retrieve an attachment metadata record by ID owned by owner_id."""
    return db.query(AttachmentModel).filter(
        AttachmentModel.id == attachment_id,
        AttachmentModel.owner_id == owner_id
    ).first()


def delete_attachment(db: Session, db_attachment: AttachmentModel) -> None:
    """Remove attachment record from database."""
    db.delete(db_attachment)
    db.commit()
