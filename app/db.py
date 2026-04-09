import sqlite3
import os
from pathlib import Path

DB_PATH = Path(os.environ.get("DECKS_DB_PATH", "spiredb.db"))

def get_db():
    conn = sqlite3.connect(DB_PATH)
    # sqlite3.Row mahdollistaa rivien käsittelyn sanakirjamaisina olioina, jolloin sarakkeisiin pääsee käsiksi nimillä esim. row["api_key"] 
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            api_key TEXT PRIMARY KEY,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS decks (
            pack_id TEXT PRIMARY KEY,
            api_key TEXT NOT NULL,
            character TEXT NOT NULL,
            deck_json TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()