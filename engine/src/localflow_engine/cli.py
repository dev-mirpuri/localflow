import argparse
import logging
import queue
import sys
import threading
import time
import wave
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import SimpleNamespace

from localflow_engine import dictate, history
from localflow_engine.cleanup import clean, warm_up_cleanup
from localflow_engine.hotkey import Hotkey
from localflow_engine.speech import load_speech, read_wav, transcribe, write_wav

HOTKEY = "right ctrl"  # Until T9 adds config.
LOG_BYTES = 1_000_000

log = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(prog="localflow-engine")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("transcribe").add_argument("wav", type=Path)
    commands.add_parser("dictate").add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")  # pyright: ignore[reportAttributeAccessIssue]
    if args.command == "dictate":
        args.data_dir.mkdir(parents=True, exist_ok=True)
        start_logging(args.data_dir / "engine.log")
        run_dictate(args.data_dir)
    else:
        start_logging(None)
        run_transcribe(args.wav)


def start_logging(path: Path | None) -> None:
    """Logs the Engine's own messages to stderr and, if given, a file of up to 2 x LOG_BYTES."""
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if path is not None:
        handlers.append(
            RotatingFileHandler(path, maxBytes=LOG_BYTES, backupCount=1, encoding="utf-8")
        )
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(module)s: %(message)s", handlers=handlers
    )
    logging.getLogger("localflow_engine").setLevel(logging.INFO)


def run_transcribe(path: Path) -> None:
    try:
        audio = read_wav(path)
    except (OSError, EOFError, wave.Error, ValueError) as error:
        sys.exit(f"Can't read {path}: {error}")

    speech = load_speech()
    start = time.perf_counter()
    transcript = transcribe(speech, audio)
    log.info("transcribe %.2f s", time.perf_counter() - start)
    print(transcript)


def run_dictate(data_dir: Path) -> None:
    # Imported here because these are Windows-only; see pyproject.toml.
    from localflow_engine import windows
    from localflow_engine.mic import Mic

    speech = load_speech()
    try:
        warm_up_cleanup()
    except Exception as error:  # Cleanup falls back to the Transcript on its own.
        log.warning("cleanup warm-up failed with %s", type(error).__name__)

    db = history.open_history(data_dir / "history.db")
    hotkey, lock, queued = Hotkey(HOTKEY), threading.Lock(), queue.Queue()
    mic = Mic(lambda value: print(f"{'#' * round(value * 20):20}", end="\r", file=sys.stderr))
    parts = SimpleNamespace(
        start=mic.start,
        stop=mic.stop,
        transcribe=lambda audio: transcribe(speech, audio),
        save_failed=lambda audio: write_wav(data_dir / "last-failed.wav", audio),
        clean=clean,
        target_app=windows.target_app,
        save=lambda raw_text, clean_text, target_app, status: history.save(
            db, raw_text, clean_text, target_app, status
        ),
        paste=windows.paste,
    )
    windows.hook(
        lambda name, scan_code, down, injected: dictate.on_key(
            hotkey, lock, queued, name, scan_code, down, injected, time.monotonic()
        )
    )
    log.info("ready: hold or double-tap Right Ctrl, Ctrl+C to quit")
    try:
        while True:
            dictate.step(hotkey, lock, queued, parts, time.monotonic)
    except KeyboardInterrupt:
        windows.unhook()
