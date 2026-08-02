# Task Management API (Build 62)

A production-ready FastAPI REST service providing user authentication (JWT + bcrypt), task management lifecycle features, CRUD operations, background tasks, and file attachments with interactive OpenAPI documentation.

## Stack
- **Language**: Python 3.12+
- **Framework**: FastAPI, Uvicorn
- **Database**: SQLite (SQLAlchemy 2.0 ORM)
- **Security & Authentication**: JWT (python-jose), bcrypt password hashing
- **Validation**: Pydantic v2 (with email-validator)
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
- `UPLOAD_DIR`: Target path for file uploads
- `MAX_UPLOAD_SIZE_BYTES`: Maximum allowed file upload size in bytes

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

## Authentication & API Usage
1. **Register Account**: `POST /auth/register` with JSON body:
   ```json
   {
     "email": "user@example.com",
     "password": "SecurePassword123!",
     "full_name": "Jane Doe"
   }
   ```
2. **Login & Obtain Token**: `POST /auth/login` (Form data: `username` and `password`). Returns JWT access token.
3. **Authenticated Task Operations**: Pass header `Authorization: Bearer <access_token>` to all protected `/tasks` endpoints.

## Architecture Notes
The application is structured into atomic Python modules under `src/task_api/`:
- `config.py`: Environment configuration via Pydantic BaseSettings.
- `auth.py`: Bcrypt password hashing, JWT encoding/decoding, and `get_current_user` FastAPI dependency.
- `database.py`: SQLAlchemy session engine and database dependency injection (`get_db`).
- `models.py`: Database ORM models (`UserModel`, `TaskModel`) establishing foreign key relationships and tenant isolation.
- `schemas.py`: Pydantic input/output schemas ensuring request validation (`UserCreate`, `TaskCreate`) and response serialization.
- `crud.py`: Encapsulated database queries filtering task data by authenticated `owner_id`.
- `main.py`: FastAPI router handling authentication routes (`/auth`) and protected task endpoints (`/tasks`).
- `cli.py`: Command Line Interface entry point supporting `--version` and `run` commands.

## Data Handling
- **Data Collected**: User profile data (email, full name, hashed password), task attributes (title, description, status, priority, due date).
- **Storage**: Retained locally in SQLite database instance specified by `DATABASE_URL`. Passwords are irreversibly hashed using bcrypt. Zero plaintext password storage.
- **Sharing**: Zero third-party data sharing. Data remains strictly isolated per user account.

## Notes
- Enforces strict tenant isolation: users can only access or mutate tasks that belong to their account.
- In-memory SQLite with `StaticPool` is configured for automated testing to ensure database state isolation per test function.
