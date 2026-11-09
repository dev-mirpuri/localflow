"""The JSON-lines protocol: one JSON object per line, stdout for the App and nothing else."""

import json
import logging
import sqlite3
import sys
import threading
from collections.abc import Callable, Iterable
from pathlib import Path

from localflow_engine import history

log = logging.getLogger(__name__)
lock = threading.Lock()  # The mic, the dictation loop and serve() all send.


def send(message: dict) -> None:
    """Writes to the real stdout: the Engine points sys.stdout at stderr for stray prints."""
    stdout = sys.__stdout__
    assert stdout is not None
    with lock:
        stdout.write(json.dumps(message) + "\n")
        stdout.flush()


def serve(
    lines: Iterable[str], data_dir: Path, config: dict, command: Callable[[str], None]
) -> None:
    """Sends config, then answers requests and passes on commands until stdin closes."""
    send(
        {"type": "config", "hotkey": config["hotkey"], "launch_at_login": config["launch_at_login"]}
    )
    db = history.open_history(data_dir / "history.db")
    for line in lines:
        try:
            message = json.loads(line)
            if message["type"] == "command":
                command(message["name"])
            else:
                send({"type": "reply", "id": message["id"], "data": answer(db, message)})
        except Exception as error:  # One bad line must not stop the Engine.
            log.error("bad message: %s", type(error).__name__)


def answer(db: sqlite3.Connection, request: dict):
    params = request["params"]
    if request["method"] == "list_history":
        return history.entries(db, params["query"], params["limit"])
    if request["method"] == "delete_entry":
        return history.delete(db, params["id"])
    raise ValueError("unknown method")
