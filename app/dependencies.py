from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader
from .db import get_db

api_key_header = APIKeyHeader(name="X-API-Key")


def is_valid_api_key(api_key: str | None) -> bool:
    if not api_key:
        return False

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT api_key FROM users WHERE api_key = ?", (api_key,))
    row = cursor.fetchone()
    conn.close()

    return row is not None

def require_api_key(api_key: str = Security(api_key_header)):
    if not is_valid_api_key(api_key):
        raise HTTPException(403, "Invalid or missing API key")

    return api_key