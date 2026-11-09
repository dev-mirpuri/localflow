"""config.json in the data folder: edited by hand, read at startup, never overwritten."""

import json
import logging
from pathlib import Path

from localflow_engine.cleanup import MODEL

log = logging.getLogger(__name__)

DEFAULTS = {
    "hotkey": "right ctrl",
    "microphone": "",
    "cleanup_model": MODEL,
    "launch_at_login": False,
}
HOTKEYS = {"right ctrl", "left ctrl", "right shift", "left shift"} | {f"f{n}" for n in range(1, 25)}
INVALID = "config.json isn't valid JSON, so it uses the defaults. Fix it and restart."
SHOWN = {"hotkey": "Right Ctrl", "microphone": "the default mic", "launch_at_login": "false"}


def load(path: Path) -> tuple[dict, list[str]]:
    """Returns the config and any Oval errors. Creates the file with the defaults if missing."""
    if not path.exists():
        try:
            path.write_text(json.dumps(DEFAULTS, indent=2) + "\n", encoding="utf-8")
        except OSError as error:  # The defaults still work without the file.
            log.error("creating config.json failed with %s", type(error).__name__)
        return dict(DEFAULTS), []
    try:
        written = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        log.error("config.json unreadable: %s", type(error).__name__)
        return dict(DEFAULTS), [INVALID]
    if not isinstance(written, dict):
        return dict(DEFAULTS), [INVALID]

    loaded, errors = dict(DEFAULTS), []
    for key, default in DEFAULTS.items():
        value = written.get(key, default)
        if key == "hotkey":
            value = value.lower() if isinstance(value, str) else ""
            valid = value in HOTKEYS
        else:
            valid = type(value) is type(default) and (key != "cleanup_model" or value)
        if valid:
            loaded[key] = value
        else:
            errors.append(invalid(key))
    return loaded, errors


def invalid(key: str) -> str:
    """The Oval error for one wrong value: it names the value and the default it uses instead."""
    fix = "Set a Ctrl, Shift or F-key." if key == "hotkey" else "Fix it and restart."
    used = SHOWN.get(key, DEFAULTS[key])
    return f"""config.json: "{key}" isn't valid, so it uses {used}. {fix}"""


def hook_name(hotkey: str) -> str:
    """The name the keyboard hook gives the key: it calls Left Ctrl "ctrl"."""
    return hotkey.removeprefix("left ")
