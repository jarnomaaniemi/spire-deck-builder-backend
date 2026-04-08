---
applyTo: app/api.py
description: "Use when editing app/api.py. Enforces route naming, response compatibility, and protected-route auth expectations."
---

# API Guidelines

## Route Naming And Structure
- Keep route handler function names in snake_case.
- Preserve existing router split:
  - `public_router` for non-auth routes.
  - `protected_router` for API-key-protected routes.
- Keep protected route registration via `APIRouter(dependencies=[Security(require_api_key)])`.
- Do not rename existing paths unless a task explicitly requires a breaking API change.

## Response Compatibility
- Treat current response shapes as stable contracts for tests and clients.
- For existing endpoints, avoid removing or renaming response keys.
- When adding fields, prefer additive changes that do not break existing consumers.
- Preserve current error semantics and messages unless the task explicitly asks to change them.

## Auth Expectations
- Protected endpoints must continue requiring `X-API-Key` through `require_api_key`.
- Missing API key behavior must remain compatible with current FastAPI security behavior.
- Invalid API key behavior must remain compatible with `require_api_key` checks.
- Keep `/auth/register` and `/auth/me` behavior aligned with the current `users` table flow.

## Card/Character ID Conventions
- Normalize character input to uppercase IDs for storage and processing.
- Keep card alias behavior intact:
  - mixed-case alias input can be accepted,
  - canonical uppercase card IDs are stored and returned where currently expected.
- Avoid introducing alternate canonical formats for IDs.

## Database And Side Effects
- Use `get_db()` from `app/db.py` for all DB interactions in this module.
- Ensure connections are closed on both success and error paths.
- Keep deck persistence in `deck_json` as JSON-encoded list of canonical card IDs.

## Sorting And Search Behavior
- Keep search filters case-insensitive for current query params (`name`, `color`, `type`, `rarity`).
- If extending sorting/filtering, make changes additive and preserve existing defaults.

## Editing Guardrails
- Prefer small, localized edits to avoid incidental API regressions.
- If behavior changes are required, update relevant tests in `tests/test_api.py` in the same task.
