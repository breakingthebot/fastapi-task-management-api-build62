# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.15.0] - 2026-08-02

### Added
- Task Dependencies and Subtask Relationships system.
- Added self-referential `parent_id` foreign key and `subtasks` relationship to `TaskModel` in `src/task_api/models.py`.
- Added `parent_id` field to `TaskCreate`, `TaskUpdate`, and `TaskResponse` schemas in `src/task_api/schemas.py`.
- Subtask listing endpoint `GET /tasks/{task_id}/subtasks` returning all active subtasks assigned under a parent task.
- Subtask validation rules in `src/task_api/crud.py` preventing self-parenting and invalid parent task references.
- Completion constraint enforcement in `src/task_api/crud.py` returning `HTTP 400 Bad Request` if a user attempts to mark a parent task completed while any of its active subtasks remain incomplete.
- Dependencies test suite in `tests/test_dependencies.py` validating subtask creation, listing, self-parenting prevention, and completion constraint rules.

## [0.14.0] - 2026-08-02

### Added
- Search Indexing & Full-Text Filters system.
- Endpoint `GET /tasks/search?q=query` enabling keyword matching across task titles, task descriptions, and task discussion comments.
- Full-text search SQL aggregation query function `search_tasks_full_text` in `src/task_api/crud.py` with multi-tenant and workspace scoping.
- Search test suite in `tests/test_search.py` validating multi-field keyword matching across titles, descriptions, and comments.

## [0.13.0] - 2026-08-02

### Added
- Soft Deletes and Task Trash Bin Recovery system.
- Added `is_deleted` (Boolean) and `deleted_at` (DateTime) columns to `TaskModel` in `src/task_api/models.py`.
- Updated `DELETE /tasks/{task_id}` to soft-delete tasks rather than immediately purging records.
- Endpoint `GET /trash/tasks` listing all soft-deleted tasks resting in user's trash bin.
- Endpoint `POST /tasks/{task_id}/restore` restoring soft-deleted tasks back into active task lists.
- Endpoint `DELETE /trash/tasks/{task_id}` for permanently purging tasks from database.
- Soft delete test suite in `tests/test_soft_delete.py` verifying soft deletion, trash bin listing, restoration, and permanent purging.

## [0.12.0] - 2026-08-02

### Added
- Task Analytics and Dashboard Statistics system.
- Endpoint `GET /analytics/tasks` returning productivity metrics (`total_tasks`, `completed_tasks`, `pending_tasks`, `completion_rate`, `tasks_by_priority`, `tasks_by_status`, `total_attachments`, `total_comments`).
- Analytical SQL query function `get_task_analytics` in `src/task_api/crud.py` with multi-tenant and workspace scoping.
- Analytics response schema `TaskAnalyticsResponse` in `src/task_api/schemas.py`.
- Analytics test suite in `tests/test_analytics.py` validating task counts, completion rate calculations, and priority distributions.

## [0.11.0] - 2026-08-02

### Added
- Rate Limiting and API Throttling system in `src/task_api/rate_limiter.py`.
- Thread-safe sliding-window `RateLimiter` service tracking request timestamps per client IP.
- Rate limiting middleware in `src/task_api/main.py` enforcing throttling on authentication endpoints (`POST /auth/login` max 5 requests per minute) and general API routes.
- Response header `Retry-After` on rate limit breaches accompanied by `HTTP 429 Too Many Requests` status code.
- Shared pytest autouse fixture in `tests/conftest.py` ensuring test isolation by resetting rate limit state between test cases.
- Rate limiter test suite in `tests/test_rate_limiter.py` covering unit window calculations, burst request rejection, and HTTP 429 integration headers.

## [0.10.0] - 2026-08-02

### Added
- Task Comments and Discussion Threads feature.
- Database model `CommentModel` storing task comments, author ID, markdown content, and timestamps.
- Post comment endpoint `POST /tasks/{task_id}/comments` and comment listing endpoint `GET /tasks/{task_id}/comments`.
- Delete comment endpoint `DELETE /comments/{comment_id}` (restricted to comment author or workspace `admin`).
- Activity audit logging trigger `comment.created` when comments are posted.
- Comment test suite in `tests/test_comments.py` covering comment creation, thread listing, deletion, and security authorization checks.

## [0.9.0] - 2026-08-02

### Added
- Team Workspaces & Role-Based Access Control (RBAC) system.
- Database models `WorkspaceModel` and `WorkspaceMemberModel` with `WorkspaceRole` enum (`admin`, `editor`, `viewer`).
- Added optional `workspace_id` foreign key on `TaskModel` to support team task sharing.
- Workspace creation endpoint `POST /workspaces` (creator automatically assigned `admin` role) and workspace listing endpoint `GET /workspaces`.
- Workspace member management endpoints `POST /workspaces/{id}/members` and `DELETE /workspaces/{id}/members/{user_id}` (restricted to workspace `admin` role).
- Fine-grained RBAC enforcement on workspace task actions (`admin` full access, `editor` create/update, `viewer` read-only).
- RBAC test suite in `tests/test_rbac.py` covering workspace creation, role assignments, member management restrictions, task sharing, and permission enforcement.

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
