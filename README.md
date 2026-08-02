# Task Management API (Build 62)

A production-ready FastAPI REST service providing user authentication (JWT + bcrypt), task management lifecycle features, CRUD operations, file attachment management, background tasks, and interactive OpenAPI documentation.

## Stack
- **Language**: Python 3.12+
- **Framework**: FastAPI, Uvicorn
- **Database**: SQLite (SQLAlchemy 2.0 ORM)
- **Security & Authentication**: JWT (python-jose), bcrypt password hashing
- **Validation**: Pydantic v2 (with email-validator)
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

## Authentication & Attachment API Usage
1. **Register Account**: `POST /auth/register`
2. **Login & Obtain Token**: `POST /auth/login` (Returns Bearer JWT token).
3. **Task Operations**: Pass header `Authorization: Bearer <access_token>` to protected `/tasks` endpoints.
4. **Upload Task Attachment**:
   ```bash
   curl -X POST "http://127.0.0.1:8000/tasks/1/attachments" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -F "file=@document.pdf"
   ```
5. **List Task Attachments**:
   ```bash
   curl http://127.0.0.1:8000/tasks/1/attachments -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
   ```
6. **Download Attachment**:
   ```bash
   curl http://127.0.0.1:8000/attachments/1/download -H "Authorization: Bearer YOUR_ACCESS_TOKEN" --output downloaded.pdf
   ```
7. **Delete Attachment**:
   ```bash
   curl -X DELETE http://127.0.0.1:8000/attachments/1 -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
   ```

## Architecture Notes
The application is structured into atomic Python modules under `src/task_api/`:
- `config.py`: Environment configuration via Pydantic BaseSettings.
- `auth.py`: Bcrypt password hashing, JWT encoding/decoding, and `get_current_user` FastAPI dependency.
- `database.py`: SQLAlchemy session engine and database dependency injection (`get_db`).
- `models.py`: Database ORM models (`UserModel`, `TaskModel`, `AttachmentModel`) establishing relationships and tenant isolation.
- `schemas.py`: Pydantic input/output schemas for Users, Tasks, and Attachment metadata responses.
- `crud.py`: Encapsulated database queries filtering tasks and attachments by authenticated `owner_id`.
- `main.py`: Main FastAPI router declaring authentication, protected tasks, and file attachment handling.
- `cli.py`: Command Line Interface entry point supporting `--version` and `run` commands.

## Data Handling
- **Data Collected**: User credentials, task details, file attachment metadata, and binary file content.
- **Storage**: Retained locally in SQLite database instance specified by `DATABASE_URL` and disk directory specified by `UPLOAD_DIR`.
- **Sharing**: Zero third-party data sharing. Attachments are strictly isolated to the uploading user account.

## Notes
- Enforces user tenant isolation on attachments: users can only list, download, or delete attachments belonging to their own tasks.
- Uploaded files are stored with unique UUID filenames to prevent path traversal vulnerabilities and filename collisions.
