from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader
from .db import get_db

api_key_header = APIKeyHeader(name="X-API-Key")

def is_valid_api_key(api_key: str | None) -> bool:
    if not api_key:
        return False
    # tietokanta yhteys
    conn = get_db()
    # "kyselykahva", joka suorittaa sql-kyselyn
    cursor = conn.cursor()
    # sql-kysely
    cursor.execute("SELECT api_key FROM users WHERE api_key = ?", (api_key,))
    # palauttaa ensimmäisen löytyneen rivin tai None
    row = cursor.fetchone()
    conn.close()
    # palauttaa True, jos rivi löytyy, muuten False
    return row is not None

def require_api_key(api_key: str = Security(api_key_header)):
    if not is_valid_api_key(api_key):
        # väärä tai puuttuva api key
        raise HTTPException(403, "Invalid or missing API key")
    # api key on validi (löytyi tietokannasta)
    return api_key