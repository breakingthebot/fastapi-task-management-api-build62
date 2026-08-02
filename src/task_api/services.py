# src/task_api/services.py
# Background processing services for asynchronous email alerts and CSV export generation.
# Connects to: src/task_api/models.py, src/task_api/config.py
# Created: 2026-08-02

import csv
import logging
import os
from datetime import datetime
from typing import List
from task_api.config import settings
from task_api.models import TaskModel, UserModel

# Setup structured logger
logger = logging.getLogger("task_api.background")
logger.setLevel(logging.INFO)


def send_urgent_task_notification(user_email: str, task_title: str, task_priority: str):
    """Simulate non-blocking background email notification dispatch for urgent/high priority tasks."""
    logger.info(
        f"[BACKGROUND TASK] Sending priority notification to {user_email} | "
        f"Task: '{task_title}' | Priority: {task_priority.upper()}"
    )


def generate_task_csv_export(export_filepath: str, user_email: str, tasks_data: List[dict]):
    """Generate CSV export file in background without blocking HTTP request thread."""
    os.makedirs(os.path.dirname(export_filepath), exist_ok=True)

    fieldnames = ["id", "title", "description", "status", "priority", "due_date", "created_at", "updated_at"]

    with open(export_filepath, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for task in tasks_data:
            writer.writerow({
                "id": task.get("id"),
                "title": task.get("title"),
                "description": task.get("description") or "",
                "status": task.get("status"),
                "priority": task.get("priority"),
                "due_date": task.get("due_date") or "",
                "created_at": task.get("created_at"),
                "updated_at": task.get("updated_at")
            })

    logger.info(f"[BACKGROUND TASK] Successfully generated task export CSV for {user_email} at {export_filepath}")
