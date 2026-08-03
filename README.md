# Task Management API (Build 62)

A production-ready FastAPI REST service providing user authentication (JWT + bcrypt), task management lifecycle features, CRUD operations, team workspaces & RBAC role-based access control (Admin, Editor, Viewer), task analytics dashboard statistics, rate limiting & sliding-window throttling (HTTP 429), task comments & discussion threads, file attachment uploads, task tagging & multi-category labeling, webhooks & real-time event subscriptions (HMAC-SHA256 signed), task activity audit trail logging, response caching & performance optimization (write-invalidation), background task processing (email alerts & CSV exports), and interactive OpenAPI documentation.

## Stack
- **Language**: Python 3.12+
- **Framework**: FastAPI, Uvicorn
- **Database**: SQLite (SQLAlchemy 2.0 ORM with Many-to-Many junction mapping & FK constraints)
- **Security & Authorization**: JWT (python-jose), bcrypt password hashing, RBAC (Admin, Editor, Viewer), HMAC-SHA256 webhooks, Rate Limiter (sliding-window)
- **Caching**: Thread-safe memory & pluggable caching service (`CacheService`) with write-invalidation
- **Validation**: Pydantic v2 (with email-validator)
- **Async & Background**: FastAPI BackgroundTasks, HTTPX
- **File Handling**: python-multipart, FileResponse
- **Testing**: pytest, HTTPX TestClient

## Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/breakingthebot/fastapi-task-management-api-build62.git
   cd fastapi-task-management-api-build62
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   # Linux/macOS:
   source venv/bin/activate
   ```

3. Install dependencies in editable mode:
   ```bash
   pip install -e .[dev]
   ```

## Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Key configuration variables:
- `APP_NAME`: Application display name
- `APP_ENV`: Environment identifier (`development` / `production`)
- `SECRET_KEY`: Secret key used for cryptographic operations and JWT signing
- `ALGORITHM`: JWT signing algorithm (default `HS256`)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: JWT token validity duration in minutes (default `30`)
- `DATABASE_URL`: SQLAlchemy database connection string (`sqlite:///./task_management.db`)
- `UPLOAD_DIR`: Target directory path for file attachments (`./uploads`)
- `MAX_UPLOAD_SIZE_BYTES`: Maximum allowed file attachment upload size in bytes (`5242880` / 5MB)

## Running Locally
Start the server using the installable CLI entry point:
```bash
task-api run --reload
```
Or directly with Uvicorn:
```bash
uvicorn task_api.main:app --reload --port 8000
```

Access the interactive OpenAPI documentation:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## Testing
Run the automated test suite with pytest:
```bash
pytest -v
```

## API Usage & Features
1. **Register & Login**: `POST /auth/register` & `POST /auth/login` to obtain a Bearer JWT access token.
2. **Task Analytics & Dashboard Metrics**: `GET /analytics/tasks` returning aggregated task totals, completion rate %, priority breakdown, status counts, attachment totals, and discussion comment metrics.
3. **Rate Limiting & Throttling**: Sliding-window counter protecting `/auth/login` (5 req/min) and general endpoints with `HTTP 429` and `Retry-After` headers.
4. **Task Comments & Discussion Threads**: `POST /tasks/{task_id}/comments`, `GET /tasks/{task_id}/comments`, `DELETE /comments/{comment_id}`.
5. **Team Workspaces & RBAC**: `POST /workspaces`, `GET /workspaces`, `POST /workspaces/{id}/members` (Admin, Editor, Viewer roles).
6. **Response Caching**: `GET /tasks` responses are cached per user with `X-Cache: HIT`/`MISS` headers and write-invalidation.
7. **Task Activity Audit Trail**: `GET /tasks/{task_id}/activity` & `GET /activity` returning revision entries and field diffs.
8. **Webhooks**: `POST /webhooks`, `GET /webhooks`, `DELETE /webhooks/{webhook_id}` with HMAC-SHA256 signature headers.
9. **Category Tagging**: `POST /tags`, `GET /tags`, `POST /tasks/{task_id}/tags/{tag_id}`, `DELETE /tasks/{task_id}/tags/{tag_id}`, `GET /tasks?tag=Work`.
10. **Task Attachments**: Upload and manage file attachments using `POST /tasks/{id}/attachments`.
11. **Background CSV Export & Priority Alerts**: `POST /tasks/export` and `GET /exports/{filename}/download`.

## Architecture Notes
The application is structured into atomic Python modules under `src/task_api/`:
- `config.py`: Environment configuration via Pydantic BaseSettings.
- `auth.py`: Bcrypt password hashing, JWT encoding/decoding, and `get_current_user` FastAPI dependency.
- `database.py`: SQLAlchemy session engine and database dependency injection (`get_db`).
- `rate_limiter.py`: Thread-safe sliding-window rate limiter class (`RateLimiter`).
- `cache.py`: High-performance thread-safe caching service (`CacheService`) with pattern invalidation.
- `models.py`: Database ORM models (`UserModel`, `TaskModel`, `AttachmentModel`, `TagModel`, `WebhookModel`, `ActivityLogModel`, `WorkspaceModel`, `WorkspaceMemberModel`, `CommentModel`).
- `schemas.py`: Pydantic input/output schemas for Users, Tasks, Workspaces, Members, Comments, Attachments, Tags, Webhooks, Activity Logs, Analytics, and Export responses.
- `crud.py`: Encapsulated database queries filtering data by authenticated `owner_id` and workspace membership.
- `services.py`: Background processing routines for non-blocking email alerts, CSV file generation, and HMAC-SHA256 webhook event dispatches.
- `main.py`: FastAPI application router mounting all REST endpoints, rate limit middleware, RBAC middleware, caching, and BackgroundTasks dependencies.
- `cli.py`: Command Line Interface entry point supporting `--version` and `run` commands.

## Data Handling
- **Data Collected**: User credentials, workspace details, team member roles, task details, discussion comments, category tags, file attachments, webhook URLs/secrets, activity audit logs, and exported CSV data files.
- **Storage**: Retained locally in SQLite database (`DATABASE_URL`), in-memory cache, and disk storage directories (`./uploads`, `./uploads/exports`).
- **Sharing**: Zero third-party data sharing. Analytics are calculated strictly for the authenticated user and their shared team workspaces.

## Notes
- Task Analytics: Dynamically calculates completion percentages and status/priority distributions via SQL aggregation.
