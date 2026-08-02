# src/task_api/services.py
# Background processing services for asynchronous email alerts, CSV export generation, and webhook dispatches.
# Connects to: src/task_api/models.py, src/task_api/config.py, src/task_api/crud.py
# Created: 2026-08-02

import csv
import hmac
import hashlib
import json
import logging
import os
import httpx
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session

from task_api.config import settings
from task_api.database import SessionLocal
from task_api.models import TaskModel, UserModel, WebhookModel

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


def dispatch_webhook_event(event_type: str, payload_data: dict, owner_id: int):
    """Dispatch HMAC-SHA256 signed HTTP POST webhook payloads to all active user-registered endpoints."""
    db: Session = SessionLocal()
    try:
        webhooks = db.query(WebhookModel).filter(
            WebhookModel.owner_id == owner_id,
            WebhookModel.is_active == True
        ).all()

        if not webhooks:
            return

        payload = {
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": payload_data
        }
        body_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")

        for wh in webhooks:
            # Generate HMAC-SHA256 signature
            signature = hmac.new(
                wh.secret_token.encode("utf-8"),
                body_bytes,
                hashlib.sha256
            ).hexdigest()

            headers = {
                "Content-Type": "application/json",
                "X-Webhook-Event": event_type,
                "X-Webhook-Signature": f"sha256={signature}"
            }

            try:
                with httpx.Client(timeout=3.0) as client:
                    response = client.post(wh.target_url, content=body_bytes, headers=headers)
                    logger.info(f"[WEBHOOK] Dispatched '{event_type}' to {wh.target_url} | Response: {response.status_code}")
            except Exception as exc:
                logger.warning(f"[WEBHOOK FAILED] Failed sending '{event_type}' to {wh.target_url}: {exc}")
    finally:
        db.close()
