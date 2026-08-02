# Task Management API (Build 62)

A production-ready FastAPI REST service providing user authentication (JWT + bcrypt), task management lifecycle features, CRUD operations, file attachment uploads, task tagging & multi-category labeling, background task processing (email alerts & CSV exports), and interactive OpenAPI documentation.

## Stack
- **Language**: Python 3.12+
- **Framework**: FastAPI, Uvicorn
- **Database**: SQLite (SQLAlchemy 2.0 ORM with Many-to-Many junction mapping)
- **Security & Authentication**: JWT (python-jose), bcrypt password hashing
- **Validation**: Pydantic v2 (with email-validator)
- **Async & Background**: FastAPI BackgroundTasks
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
2. **Category Tagging**:
   - **Create Tag**: `POST /tags` with `{"name": "Frontend", "color": "#007bff"}`
   - **List User Tags**: `GET /tags`
   - **Attach Tag to Task**: `POST /tasks/{task_id}/tags/{tag_id}`
   - **Remove Tag from Task**: `DELETE /tasks/{task_id}/tags/{tag_id}`
   - **Filter Tasks by Tag**: `GET /tasks?tag=Frontend`
3. **Task Creation & Urgent Alerts**: Creating a task with priority `high` or `urgent` automatically triggers a non-blocking background notification log.
4. **Task Attachments**: Upload and manage file attachments using `POST /tasks/{id}/attachments`.
5. **Background CSV Export**: Trigger background task via `POST /tasks/export` and download generated CSV via `GET /exports/{filename}/download`.

## Architecture Notes
The application is structured into atomic Python modules under `src/task_api/`:
- `config.py`: Environment configuration via Pydantic BaseSettings.
- `auth.py`: Bcrypt password hashing, JWT encoding/decoding, and `get_current_user` FastAPI dependency.
- `database.py`: SQLAlchemy session engine and database dependency injection (`get_db`).
- `models.py`: Database ORM models (`UserModel`, `TaskModel`, `AttachmentModel`, `TagModel`) with `task_tags` junction table.
- `schemas.py`: Pydantic input/output schemas for Users, Tasks, Attachments, Tags, and Background Export responses.
- `crud.py`: Encapsulated database queries filtering data and tag associations by authenticated `owner_id`.
- `services.py`: Background processing routines for non-blocking email alerts and CSV file generation.
- `main.py`: FastAPI application router mounting all REST endpoints and BackgroundTasks dependencies.
- `cli.py`: Command Line Interface entry point supporting `--version` and `run` commands.

## Data Handling
- **Data Collected**: User credentials, task details, category tags, file attachments, and exported CSV data files.
- **Storage**: Retained locally in SQLite database (`DATABASE_URL`) and disk storage directories (`./uploads`, `./uploads/exports`).
- **Sharing**: Zero third-party data sharing. Tags, export files, and attachments are strictly isolated to the owning user account.

## Notes
- Many-to-many relationship: Tasks and Tags use a normalized junction table (`task_tags`) for multi-category organization.
- Non-blocking execution: Background tasks offload email alerts and CSV file generation outside the HTTP request loop.
