# Project Guidelines

## Code Style
- Keep Python code simple and explicit, matching the existing FastAPI style in `main.py` and `app/api.py`.
- Preserve current naming conventions:
  - API route functions use snake_case.
  - Card and character IDs are treated as uppercase identifiers (for example `BASH`, `IRONCLAD`), while inputs may come in mixed case.
- Keep comments concise.
- Write new and edited code comments in English.
- When touching an existing comment, translate it to English instead of leaving it in another language.

## Architecture
- Entry point: `main.py` creates the FastAPI app, includes the shared router from `app/api.py`, and redirects `/` to `/docs`.
- API layer: `app/api.py`
  - Public routes: `/auth/*`, `/characters*`, `/search/cards`.
  - Protected routes: `/deck/*`, `/decks` (guarded with `Security(require_api_key)`).
- Auth dependency: `app/dependencies.py` validates `X-API-Key` against the `users` table.
- Data loading: `app/loader.py` loads JSON data from `data/*.json` and normalizes list payloads into dicts by `id`.
- Deck calculations: `app/deck_logic.py` computes damage/block totals and adjusted per-turn stats.
- Persistence: `app/db.py` uses SQLite and `DECKS_DB_PATH` (defaults to `spiredb.db`).

## Build And Test
- Create venv (PowerShell): `python -m venv venv` then `& venv\Scripts\Activate.ps1`
- Install deps: `pip install -r requirements.txt`
- Run API locally: `uvicorn main:app --reload`
- Run tests: `pytest`
- Useful test variants: `pytest -q`, `pytest -vv`, `pytest -k api`

## Conventions
- Keep API responses backward-compatible for existing tests unless task explicitly requests behavior changes.
- Preserve alias behavior for cards:
  - `resolve_card_id` accepts camel-style aliases and uppercase IDs.
  - Deck storage uses resolved canonical IDs.
- Keep protected-route behavior consistent:
  - Missing or invalid API keys should continue returning auth errors through `require_api_key`.
- When adding DB-related tests, isolate DB state via `DECKS_DB_PATH` and clean up test DB files.

## Key References
- Project overview and endpoint summary: `README.md`
- API and route patterns: `app/api.py`
- DB bootstrap and env override: `app/db.py`
- Stats logic patterns: `app/deck_logic.py`
- Loader and data-shape assumptions: `app/loader.py`
