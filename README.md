# Task Management API (Build 62)

A production-ready FastAPI REST service providing complete task management lifecycle features, CRUD operations, background tasks, authentication, and file attachments with interactive OpenAPI documentation.

## Stack
- **Language**: Python 3.12+
- **Framework**: FastAPI, Uvicorn
- **Database**: SQLite (SQLAlchemy 2.0 ORM)
- **Validation**: Pydantic v2
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
- `SECRET_KEY`: Secret key used for cryptographic operations
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

## Architecture Notes
The application is structured into atomic Python modules under `src/task_api/`:
- `config.py`: Environment configuration via Pydantic BaseSettings.
- `database.py`: SQLAlchemy session engine and database dependency injection (`get_db`).
- `models.py`: Database ORM models representing tasks with status and priority enums.
- `schemas.py`: Pydantic input/output schemas ensuring strict request validation and response serialization.
- `crud.py`: Encapsulated database operations keeping route handlers lean.
- `main.py`: Main FastAPI router and middleware initialization.
- `cli.py`: Command Line Interface entry point supporting `--version` and `run` commands.

## Data Handling
- **Data Collected**: Task details (title, description, status, priority, due date).
- **Storage**: Retained locally in SQLite database instance specified by `DATABASE_URL`. No external tracking or user analytics stored.
- **Sharing**: Zero third-party data sharing. Data remains isolated to the local runtime environment.

## Notes
- Built using clean layered architecture separating data models, Pydantic schemas, CRUD operations, and HTTP routing.
- In-memory SQLite with `StaticPool` is configured for automated testing to ensure database state isolation per test function.
