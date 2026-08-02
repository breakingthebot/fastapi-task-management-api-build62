# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.0] - 2026-08-02

### Added
- Response Caching & Performance Optimization system in `src/task_api/cache.py`.
- Thread-safe `CacheService` with configurable TTL expiration and pattern-based user cache invalidation.
- Response header `X-Cache` (`HIT` / `MISS`) indicating cached vs fresh database query responses on `GET /tasks`.
- Automatic write-invalidation triggering on task creation (`POST /tasks`), updates (`PUT /tasks/{id}`), deletions (`DELETE /tasks/{id}`), and tag associations (`POST/DELETE /tasks/{id}/tags/{id}`).
- Cache test suite in `tests/test_cache.py` covering cache HIT/MISS headers, write-invalidation on task mutations, and multi-tenant cache key isolation.

## [0.7.0] - 2026-08-02

### Added
- Task Activity Logging and Revision Audit Trail system.
- Database model `ActivityLogModel` storing immutable action logs (`task.created`, `task.updated`, `task.deleted`, `tag.attached`, `tag.removed`, `attachment.uploaded`, `attachment.deleted`).
- Granular field-level diff tracking (`field_changed`, `old_value`, `new_value`) on task updates.
- Task activity audit log endpoint `GET /tasks/{task_id}/activity`.
- User overall activity audit trail endpoint `GET /activity`.
- Activity log test suite in `tests/test_activity.py` covering creation logs, field diffs, tag/attachment events, overall audit retrieval, and tenant security isolation.

## [0.6.0] - 2026-08-02

### Added
- Webhooks & Real-Time Event Subscription system.
- Database model `WebhookModel` storing target receiver URLs, secret signing tokens, and active states.
- Webhook registration endpoint `POST /webhooks`, listing endpoint `GET /webhooks`, and deletion endpoint `DELETE /webhooks/{webhook_id}`.
- Async background webhook event dispatcher (`dispatch_webhook_event`) using HTTPX.
- HMAC-SHA256 signature calculation over raw JSON payloads, sent in header `X-Webhook-Signature` (`sha256=...`).
- Automatic webhook dispatches triggered on `task.created`, `task.updated`, and `task.deleted` lifecycle events.
- Webhook test suite in `tests/test_webhooks.py` covering registration, listing, deletion, HMAC signature calculation, and tenant isolation.

## [0.5.0] - 2026-08-02

### Added
- Task Tagging and Multi-Category Labeling feature.
- Database model `TagModel` and `task_tags` many-to-many junction table.
- Create tag endpoint `POST /tags` with hex color support and duplicate name validation per user.
- List tags endpoint `GET /tags` returning user tags.
- Tag association endpoints `POST /tasks/{task_id}/tags/{tag_id}` and `DELETE /tasks/{task_id}/tags/{tag_id}`.
- Tag-based task query filtering via `GET /tasks?tag={name}`.
- Tag test suite in `tests/test_tags.py` covering creation, listing, task linking/unlinking, tag filtering, and tenant security isolation.

## [0.4.0] - 2026-08-02

### Added
- Background task execution framework using FastAPI `BackgroundTasks`.
- Non-blocking urgent task notification dispatch service (`send_urgent_task_notification`).
- Asynchronous CSV task export processing endpoint `POST /tasks/export` returning HTTP 202 Accepted.
- Export file download endpoint `GET /exports/{filename}/download` with security checks.
- Background services module `src/task_api/services.py` handling file generation and logging.
- Background task test suite in `tests/test_background.py` covering urgent task triggers, CSV exports, and multi-tenant download isolation.

## [0.3.0] - 2026-08-02

### Added
- Task File Attachment feature supporting document and image file uploads linked to tasks.
- Database model `AttachmentModel` storing metadata (filename, stored filename, content type, size, upload timestamp).
- Upload endpoint `POST /tasks/{task_id}/attachments` with multipart upload support, file size limits (`MAX_UPLOAD_SIZE_BYTES`), and UUID stored filename security.
- List attachments endpoint `GET /tasks/{task_id}/attachments` returning attachment metadata.
- Download endpoint `GET /attachments/{attachment_id}/download` streaming files via `FileResponse`.
- Delete attachment endpoint `DELETE /attachments/{attachment_id}` with disk file cleanup.
- Strict multi-tenant attachment isolation ensuring users can only download or delete their own attachments.
- Attachment test suite in `tests/test_attachments.py` covering upload, listing, download, deletion, and security checks.

## [0.2.0] - 2026-08-02

### Added
- User authentication framework with bcrypt password hashing and JWT token issuance.
- New database model `UserModel` and foreign key `owner_id` relationship on `TaskModel`.
- User registration endpoint `POST /auth/register` and duplicate email validation.
- Login endpoint `POST /auth/login` returning Bearer JWT access tokens.
- Profile endpoint `GET /auth/me` returning current user details.
- `get_current_user` dependency enforcing JWT token validation across all `/tasks` endpoints.
- Strict multi-tenant user isolation (users only access their own tasks).
- Unit & integration tests for authentication (`tests/test_auth.py`) and tenant isolation (`tests/test_tasks.py`).
- Dependency updates: added `email-validator` for Pydantic `EmailStr` field validation.

## [0.1.0] - 2026-08-02

### Added
- Core FastAPI application with health check (`/health`) and version (`/version`) endpoints.
- SQLAlchemy Task ORM model and SQLite database integration.
- Pydantic v2 schemas for task creation, update, listing, and OpenAPI schema generation.
- Complete CRUD API endpoints (`POST /tasks`, `GET /tasks`, `GET /tasks/{id}`, `PUT /tasks/{id}`, `DELETE /tasks/{id}`).
- Filtering by status and priority, pagination (`skip`, `limit`), and search support.
- Installable CLI entry point `task-api` with `--version` and `run` flags.
- Unit and integration test suite using pytest and FastAPI TestClient.
- GitHub Actions CI workflow (`.github/workflows/ci.yml`).
- MIT License and project metadata files (`pyproject.toml`, `requirements.txt`, `.env.example`, `.gitignore`).
