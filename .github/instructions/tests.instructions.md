---
applyTo: tests/**/*.py
description: "Use when creating or editing pytest files under tests/. Enforces fixture structure, API test style, auth expectations, and DB isolation for this project."
---

# Test Guidelines

## Fixture Patterns
- Define shared fixtures explicitly with `@pytest.fixture`; do not rely on implicit or unreachable fixture code.
- Keep fixtures single-purpose. Example split:
  - `api_key` registers a user via `/auth/register` and returns only the key.
  - `deck_pack_id` depends on `api_key`, creates a deck, and returns only `pack_id`.
- Never place executable test setup after a `return` inside fixtures.
- Prefer `scope="function"` for stateful API fixtures unless a wider scope is necessary.
- In `tests/test_api.py`, keep the `api_key` fixture separate from `deck_pack_id` so fixture dependencies stay explicit.

## DB Isolation
- API tests must isolate SQLite state from the committed `spiredb.db`.
- Set `os.environ["DECKS_DB_PATH"] = "spiredb_test.db"` before importing `main` or any module that initializes DB state.
- Use a cleanup fixture (typically session `autouse=True`) to delete `spiredb_test.db` after tests.
- If a test creates additional temp DB files, clean them up in teardown.

## API Test Style
- Use `TestClient` against `main.app`.
- Assert both HTTP status codes and key response fields, not status alone.
- Keep endpoint behavior assertions aligned with current API contracts in `app/api.py`.
- For protected routes, validate both auth failures:
  - Missing `X-API-Key` -> `401`
  - Invalid `X-API-Key` -> `403`

## Card And Character Conventions In Tests
- Treat canonical IDs as uppercase (for example `BASH`, `IRONCLAD`).
- Mixed-case card input is valid in requests where alias resolution is expected (for example `Bash`), but persisted deck IDs should assert canonical uppercase values.

## Safety Checks
- Avoid mutating production-like DB files or relying on existing local DB contents.
- Keep tests deterministic: no external network calls, no system-time assumptions unless explicitly asserted.
