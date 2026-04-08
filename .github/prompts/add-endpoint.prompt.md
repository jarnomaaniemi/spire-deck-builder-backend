---
description: "Add or modify an API endpoint in this repo with compatible responses, focused tests, and a docs checklist."
name: "Add Endpoint Workflow"
argument-hint: "Describe method/path/auth, request/response shape, and validation rules"
agent: "agent"
---
Add or modify a FastAPI endpoint in this workspace using the user request as the source of truth.

Follow project instructions:
- Workspace rules: [copilot-instructions](../copilot-instructions.md)
- API file rules: [api.instructions](../instructions/api.instructions.md)
- Test file rules: [tests.instructions](../instructions/tests.instructions.md)

Task checklist:
1. Parse the requested endpoint behavior from the prompt arguments.
2. Update [app/api.py](../../app/api.py) with minimal, localized edits:
   - Keep route handler names in snake_case.
   - Preserve router boundaries (`public_router` vs `protected_router`).
   - Keep protected endpoints using `Security(require_api_key)`.
   - Preserve existing response contracts unless the request explicitly asks for a breaking change.
3. Add or update tests in [tests/test_api.py](../../tests/test_api.py):
   - Cover success path and relevant failure paths.
   - For protected routes, assert missing key (`401`) and invalid key (`403`) where applicable.
   - Keep DB isolation via `DECKS_DB_PATH` test DB usage.
4. Apply docs checklist:
   - If endpoint inventory changed, update endpoint summary in [README.md](../../README.md).
   - If no doc changes are needed, state why.
5. Validate changes:
   - Always run targeted tests automatically first (`pytest -k api`) unless the user explicitly says not to run tests.
   - Run broader tests (`pytest`) when practical after targeted tests pass.
   - Report what was run and any remaining gaps.

Output format:
- `Implemented`: short summary of endpoint behavior and auth model.
- `Files Changed`: bullet list with what changed in each file.
- `Test Results`: commands run and pass/fail summary.
- `Docs Checklist`: updated/not-updated with reason.
- `Follow-ups`: optional next improvements if relevant.

Guardrails:
- Do not silently change unrelated endpoint behavior.
- Keep edits backward-compatible by default.
- If requirements are ambiguous, ask one concise clarification question before editing.
