# Task Management API (Build 62)

A production-ready FastAPI REST service providing user authentication (JWT + bcrypt), task management lifecycle features, CRUD operations, team workspaces & RBAC role-based access control (Admin, Editor, Viewer), file attachment uploads, task tagging & multi-category labeling, webhooks & real-time event subscriptions (HMAC-SHA256 signed), task activity audit trail logging, response caching & performance optimization (write-invalidation), background task processing (email alerts & CSV exports), and interactive OpenAPI documentation.

## Stack
- **Language**: Python 3.12+
- **Framework**: FastAPI, Uvicorn
- **Database**: SQLite (SQLAlchemy 2.0 ORM with Many-to-Many junction mapping & FK constraints)
- **Security & Authorization**: JWT (python-jose), bcrypt password hashing, RBAC (Admin, Editor, Viewer), HMAC-SHA256 webhooks
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
2. **Team Workspaces & RBAC Role Management**:
   - **Create Workspace**: `POST /workspaces` with `{"name": "Engineering", "description": "Backend Team"}` (Creator automatically assigned `admin` role).
   - **List Workspaces**: `GET /workspaces`
   - **Add Member**: `POST /workspaces/{id}/members` with `{"user_email": "jane@example.com", "role": "editor"}` (Admin only).
   - **Remove Member**: `DELETE /workspaces/{id}/members/{user_id}` (Admin only).
   - **Permissions**:
     - **Admin**: Full access (manage members, create, edit, delete tasks).
     - **Editor**: Create and update workspace tasks.
     - **Viewer**: Read-only access to workspace tasks.
3. **Response Caching**: `GET /tasks` responses are cached per user with `X-Cache: HIT`/`MISS` headers and write-invalidation.
4. **Task Activity Audit Trail**: `GET /tasks/{task_id}/activity` & `GET /activity` returning revision entries and field diffs.
5. **Webhooks**: `POST /webhooks`, `GET /webhooks`, `DELETE /webhooks/{webhook_id}` with HMAC-SHA256 signature headers.
6. **Category Tagging**: `POST /tags`, `GET /tags`, `POST /tasks/{task_id}/tags/{tag_id}`, `DELETE /tasks/{task_id}/tags/{tag_id}`, `GET /tasks?tag=Work`.
7. **Task Attachments**: Upload and manage file attachments using `POST /tasks/{id}/attachments`.
8. **Background CSV Export & Priority Alerts**: `POST /tasks/export` and `GET /exports/{filename}/download`.

## Architecture Notes
The application is structured into atomic Python modules under `src/task_api/`:
- `config.py`: Environment configuration via Pydantic BaseSettings.
- `auth.py`: Bcrypt password hashing, JWT encoding/decoding, and `get_current_user` FastAPI dependency.
- `database.py`: SQLAlchemy session engine and database dependency injection (`get_db`).
- `cache.py`: High-performance thread-safe caching service (`CacheService`) with pattern invalidation.
- `models.py`: Database ORM models (`UserModel`, `TaskModel`, `AttachmentModel`, `TagModel`, `WebhookModel`, `ActivityLogModel`, `WorkspaceModel`, `WorkspaceMemberModel`).
- `schemas.py`: Pydantic input/output schemas for Users, Tasks, Workspaces, Members, Attachments, Tags, Webhooks, Activity Logs, and Export responses.
- `crud.py`: Encapsulated database queries filtering data by authenticated `owner_id` and workspace membership.
- `services.py`: Background processing routines for non-blocking email alerts, CSV file generation, and HMAC-SHA256 webhook event dispatches.
- `main.py`: FastAPI application router mounting all REST endpoints, RBAC middleware, caching, and BackgroundTasks dependencies.
- `cli.py`: Command Line Interface entry point supporting `--version` and `run` commands.

## Data Handling
- **Data Collected**: User credentials, workspace details, team member roles, task details, category tags, file attachments, webhook URLs/secrets, activity audit logs, and exported CSV data files.
- **Storage**: Retained locally in SQLite database (`DATABASE_URL`), in-memory cache, and disk storage directories (`./uploads`, `./uploads/exports`).
- **Sharing**: Zero third-party data sharing. Workspaces are accessible only to explicitly added team members.

## Notes
- RBAC Rules: Permissions are enforced at the API route level based on assigned `WorkspaceRole` (`admin`, `editor`, `viewer`).
