import sqlite3
from datetime import datetime

from localflow_engine import history


def rows(path) -> list[sqlite3.Row]:
    """Reads the table as the app will: the columns are the contract, not the module."""
    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        return db.execute("SELECT * FROM entries ORDER BY id").fetchall()


def test_a_saved_entry_is_on_disk_with_every_column(tmp_path):
    path = tmp_path / "history.db"
    db = history.open_history(path)

    entry = history.save(db, "um hello there", "Hello there.", "notepad.exe", "raw_fallback")

    [row] = rows(path)
    assert dict(row) == entry
    assert dict(row) | {"created_at": None} == {
        "id": entry["id"],
        "created_at": None,
        "raw_text": "um hello there",
        "clean_text": "Hello there.",
        "target_app": "notepad.exe",
        "status": "raw_fallback",
    }
    assert datetime.fromisoformat(row["created_at"]).tzinfo is not None


def test_reopening_keeps_earlier_entries_and_adds_after_them(tmp_path):
    path = tmp_path / "history.db"
    first = history.save(history.open_history(path), "one", "One.", "a.exe", "ok")["id"]
    second = history.save(history.open_history(path), "two", "Two.", "b.exe", "ok")["id"]

    assert second > first
    assert [row["clean_text"] for row in rows(path)] == ["One.", "Two."]
