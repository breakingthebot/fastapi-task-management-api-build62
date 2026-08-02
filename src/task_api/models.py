# src/task_api/models.py
# SQLAlchemy ORM Data Models for User Accounts, Tasks, File Attachments, and Tags.
# Connects to: src/task_api/database.py, src/task_api/crud.py, src/task_api/auth.py
# Created: 2026-08-02

import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, Boolean, Table
from sqlalchemy.orm import relationship
from task_api.database import Base


def utc_now():
    """Return timezone-naive UTC timestamp for SQLite compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TaskStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# Junction table for Many-to-Many relationship between Tasks and Tags
task_tags = Table(
    "task_tags",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
)


class UserModel(Base):
    """SQLAlchemy User model storing account authentication data."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    tasks = relationship("TaskModel", back_populates="owner", cascade="all, delete-orphan")
    attachments = relationship("AttachmentModel", back_populates="owner", cascade="all, delete-orphan")
    tags = relationship("TagModel", back_populates="owner", cascade="all, delete-orphan")


class TagModel(Base):
    """SQLAlchemy Tag model for categorizing tasks with labels and colors."""
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(64), nullable=False, index=True)
    color = Column(String(32), default="#6c757d", nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    owner = relationship("UserModel", back_populates="tags")
    tasks = relationship("TaskModel", secondary=task_tags, back_populates="tags")


class TaskModel(Base):
    """SQLAlchemy Task model storing user task records."""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.TODO, nullable=False, index=True)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False, index=True)
    due_date = Column(DateTime, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    owner = relationship("UserModel", back_populates="tasks")
    attachments = relationship("AttachmentModel", back_populates="task", cascade="all, delete-orphan")
    tags = relationship("TagModel", secondary=task_tags, back_populates="tasks")


class AttachmentModel(Base):
    """SQLAlchemy Attachment model storing metadata for task file uploads."""
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False, unique=True)
    file_path = Column(String(512), nullable=False)
    content_type = Column(String(128), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    uploaded_at = Column(DateTime, default=utc_now, nullable=False)

    task = relationship("TaskModel", back_populates="attachments")
    owner = relationship("UserModel", back_populates="attachments")
