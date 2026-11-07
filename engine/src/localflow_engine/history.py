"""History: every finished Dictation as an Entry in one SQLite table."""

import sqlite3
from datetime import datetime
from pathlib import Path


def open_history(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute(
        "CREATE TABLE IF NOT EXISTS entries (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL,"
        " raw_text TEXT NOT NULL, clean_text TEXT NOT NULL, target_app TEXT NOT NULL,"
        " status TEXT NOT NULL CHECK (status IN ('ok', 'raw_fallback')))"
    )
    return db


def save(
    db: sqlite3.Connection, raw_text: str, clean_text: str, target_app: str, status: str
) -> dict:
    """Saves an Entry, committed before returning, and returns it."""
    created_at = datetime.now().astimezone().isoformat(timespec="seconds")
    with db:
        cursor = db.execute(
            "INSERT INTO entries (created_at, raw_text, clean_text, target_app, status)"
            " VALUES (?, ?, ?, ?, ?)",
            (created_at, raw_text, clean_text, target_app, status),
        )
    return dict(db.execute("SELECT * FROM entries WHERE id = ?", (cursor.lastrowid,)).fetchone())


def entries(db: sqlite3.Connection, query: str, limit: int) -> list[dict]:
    """The newest Entries first, up to limit, whose clean_text contains query in any case."""
    rows = db.execute(
        "SELECT * FROM entries WHERE instr(lower(clean_text), lower(?)) > 0"
        " ORDER BY id DESC LIMIT ?",
        (query, limit),
    )
    return [dict(row) for row in rows]


def delete(db: sqlite3.Connection, entry_id: int) -> None:
    with db:
        db.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
