# src/task_api/crud.py
# Database interaction logic and queries for User, Task, Attachment, Tag, Webhook, ActivityLog, Workspace, Comment, and Analytics objects.
# Connects to: src/task_api/models.py, src/task_api/schemas.py, src/task_api/auth.py
# Created: 2026-08-02

import secrets
from typing import Optional, List, Tuple, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func
from task_api.models import (
    UserModel, TaskModel, AttachmentModel, TagModel, WebhookModel, ActivityLogModel,
    WorkspaceModel, WorkspaceMemberModel, CommentModel, WorkspaceRole, TaskStatus, TaskPriority
)
from task_api.schemas import UserCreate, TaskCreate, TaskUpdate, TagCreate, WebhookCreate, WorkspaceCreate, CommentCreate
from task_api.auth import get_password_hash


# Analytics CRUD Operations
def get_task_analytics(db: Session, owner_id: int) -> Dict:
    """Compute aggregated dashboard analytics and productivity metrics for a user."""
    user_workspace_ids = [w.id for w in get_user_workspaces(db=db, user_id=owner_id)]

    base_query = db.query(TaskModel).filter(
        (TaskModel.owner_id == owner_id) | (TaskModel.workspace_id.in_(user_workspace_ids) if user_workspace_ids else False)
    )

    total_tasks = base_query.count()
    completed_tasks = base_query.filter(TaskModel.status == TaskStatus.COMPLETED).count()
    pending_tasks = total_tasks - completed_tasks
    completion_rate = round((completed_tasks / total_tasks * 100.0), 2) if total_tasks > 0 else 0.0

    # Tasks by priority
    priority_counts = {p.value: 0 for p in TaskPriority}
    priority_results = db.query(TaskModel.priority, func.count(TaskModel.id)).filter(
        (TaskModel.owner_id == owner_id) | (TaskModel.workspace_id.in_(user_workspace_ids) if user_workspace_ids else False)
    ).group_by(TaskModel.priority).all()
    for priority_enum, count in priority_results:
        priority_counts[priority_enum.value] = count

    # Tasks by status
    status_counts = {s.value: 0 for s in TaskStatus}
    status_results = db.query(TaskModel.status, func.count(TaskModel.id)).filter(
        (TaskModel.owner_id == owner_id) | (TaskModel.workspace_id.in_(user_workspace_ids) if user_workspace_ids else False)
    ).group_by(TaskModel.status).all()
    for status_enum, count in status_results:
        status_counts[status_enum.value] = count

    # Attachments & Comments counts
    total_attachments = db.query(AttachmentModel).filter(AttachmentModel.owner_id == owner_id).count()
    total_comments = db.query(CommentModel).filter(CommentModel.author_id == owner_id).count()

    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "completion_rate": completion_rate,
        "tasks_by_priority": priority_counts,
        "tasks_by_status": status_counts,
        "total_attachments": total_attachments,
        "total_comments": total_comments
    }


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


# Comment CRUD Operations
def create_comment(db: Session, task_id: int, author_id: int, comment_in: CommentCreate) -> CommentModel:
    """Persist a new task comment."""
    db_comment = CommentModel(
        task_id=task_id,
        author_id=author_id,
        content=comment_in.content
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment


def get_task_comments(db: Session, task_id: int) -> List[CommentModel]:
    """Retrieve all comments posted on a task."""
    return db.query(CommentModel).filter(CommentModel.task_id == task_id).order_by(CommentModel.id.asc()).all()


def get_comment_by_id(db: Session, comment_id: int) -> Optional[CommentModel]:
    """Retrieve a comment by ID."""
    return db.query(CommentModel).filter(CommentModel.id == comment_id).first()


def delete_comment(db: Session, db_comment: CommentModel) -> None:
    """Delete a comment."""
    db.delete(db_comment)
    db.commit()


# Workspace & RBAC CRUD Operations
def create_workspace(db: Session, workspace_in: WorkspaceCreate, owner_id: int) -> WorkspaceModel:
    """Create a new team workspace and automatically add owner as ADMIN."""
    db_workspace = WorkspaceModel(
        name=workspace_in.name,
        description=workspace_in.description,
        owner_id=owner_id
    )
    db.add(db_workspace)
    db.commit()
    db.refresh(db_workspace)

    owner_member = WorkspaceMemberModel(
        workspace_id=db_workspace.id,
        user_id=owner_id,
        role=WorkspaceRole.ADMIN
    )
    db.add(owner_member)
    db.commit()
    db.refresh(db_workspace)

    return db_workspace


def get_user_workspaces(db: Session, user_id: int) -> List[WorkspaceModel]:
    """Retrieve all workspaces where the user is a member or owner."""
    return db.query(WorkspaceModel).join(WorkspaceMemberModel).filter(
        WorkspaceMemberModel.user_id == user_id
    ).all()


def get_workspace_by_id(db: Session, workspace_id: int) -> Optional[WorkspaceModel]:
    """Retrieve a workspace by ID."""
    return db.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).first()


def get_workspace_member(db: Session, workspace_id: int, user_id: int) -> Optional[WorkspaceMemberModel]:
    """Retrieve workspace membership record for user."""
    return db.query(WorkspaceMemberModel).filter(
        WorkspaceMemberModel.workspace_id == workspace_id,
        WorkspaceMemberModel.user_id == user_id
    ).first()


def get_workspace_member_role(db: Session, workspace_id: int, user_id: int) -> Optional[WorkspaceRole]:
    """Get assigned RBAC role for user in workspace."""
    member = get_workspace_member(db=db, workspace_id=workspace_id, user_id=user_id)
    return member.role if member else None


def add_workspace_member(db: Session, workspace_id: int, user_id: int, role: WorkspaceRole) -> WorkspaceMemberModel:
    """Add user to workspace with specified RBAC role or update existing role."""
    member = get_workspace_member(db=db, workspace_id=workspace_id, user_id=user_id)
    if member:
        member.role = role
    else:
        member = WorkspaceMemberModel(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role
        )
        db.add(member)
    db.commit()
    db.refresh(member)
    return member


def remove_workspace_member(db: Session, member: WorkspaceMemberModel) -> None:
    """Remove user from workspace."""
    db.delete(member)
    db.commit()


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
        ActivityLogModel.task_id == task_id
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


# Task CRUD Operations (User & Workspace Scoped)
def create_task(db: Session, task_in: TaskCreate, owner_id: int) -> TaskModel:
    """Create a new task record linked to an owner_id and optional workspace_id."""
    db_task = TaskModel(
        title=task_in.title,
        description=task_in.description,
        status=task_in.status,
        priority=task_in.priority,
        due_date=task_in.due_date,
        owner_id=owner_id,
        workspace_id=task_in.workspace_id
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def get_task_by_id(db: Session, task_id: int, owner_id: int) -> Optional[TaskModel]:
    """Retrieve a single task owned by user or in a workspace where user is a member."""
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        return None

    if task.owner_id == owner_id:
        return task

    if task.workspace_id:
        role = get_workspace_member_role(db=db, workspace_id=task.workspace_id, user_id=owner_id)
        if role is not None:
            return task

    return None


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
    """Retrieve a paginated list of tasks owned by user or shared in user's workspaces."""
    user_workspace_ids = [w.id for w in get_user_workspaces(db=db, user_id=owner_id)]

    query = db.query(TaskModel).filter(
        (TaskModel.owner_id == owner_id) | (TaskModel.workspace_id.in_(user_workspace_ids) if user_workspace_ids else False)
    )

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
    """List all attachments linked to a task owned by owner_id or in shared workspace."""
    task = get_task_by_id(db=db, task_id=task_id, owner_id=owner_id)
    if not task:
        return []

    return db.query(AttachmentModel).filter(
        AttachmentModel.task_id == task_id
    ).all()


def get_attachment_by_id_and_owner(db: Session, attachment_id: int, owner_id: int) -> Optional[AttachmentModel]:
    """Retrieve an attachment metadata record by ID owned by owner_id or in a shared workspace."""
    attachment = db.query(AttachmentModel).filter(AttachmentModel.id == attachment_id).first()
    if not attachment:
        return None

    if attachment.owner_id == owner_id:
        return attachment

    if attachment.task and attachment.task.workspace_id:
        role = get_workspace_member_role(db=db, workspace_id=attachment.task.workspace_id, user_id=owner_id)
        if role is not None:
            return attachment

    return None


def delete_attachment(db: Session, db_attachment: AttachmentModel) -> None:
    """Remove attachment record from database."""
    db.delete(db_attachment)
    db.commit()
