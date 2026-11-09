import argparse
import logging
import os
import queue
import sys
import threading
import time
import wave
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import SimpleNamespace

from localflow_engine import config, dictate, history, protocol, speech
from localflow_engine.cleanup import clean, unload_cleanup, warm_up_cleanup
from localflow_engine.hotkey import Hotkey
from localflow_engine.speech import load_speech, read_wav, transcribe, write_wav

LOG_BYTES = 1_000_000

log = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(prog="localflow-engine")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("transcribe").add_argument("wav", type=Path)
    commands.add_parser("dictate").add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()

    sys.stdin.reconfigure(encoding="utf-8")  # pyright: ignore[reportAttributeAccessIssue]
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

    models = load_speech()
    start = time.perf_counter()
    transcript = transcribe(models, audio)
    log.info("transcribe %.2f s", time.perf_counter() - start)
    print(transcript)


def run_dictate(data_dir: Path) -> None:
    """The Engine as the App runs it: JSON lines on stdin and stdout, until stdin closes."""
    # Imported here because it is Windows-only; see pyproject.toml.
    from localflow_engine import windows

    sys.stdout = sys.stderr  # Only protocol.send() writes to the real stdout.
    settings, errors = config.load(data_dir / "config.json")
    for message in errors:
        protocol.send({"type": "error", "message": message})
    hotkey = Hotkey(config.hook_name(settings["hotkey"]))
    lock, queued = threading.Lock(), queue.Queue()
    startup = SimpleNamespace(state="loading", held=False, shown=False, error="")

    def on_key(name: str, scan_code: int, down: bool, injected: bool) -> bool:
        if dictate.held_back(startup, hotkey.name, name, down, injected, protocol.send):
            return False
        now = time.monotonic()
        return dictate.on_key(hotkey, lock, queued, name, scan_code, down, injected, now)

    windows.hook(on_key)
    threading.Thread(
        target=run_dictation, args=(data_dir, settings, hotkey, lock, queued, startup), daemon=True
    ).start()
    try:
        protocol.serve(
            sys.stdin,
            data_dir,
            settings,
            lambda name: dictate.on_command(hotkey, lock, queued, name, time.monotonic()),
        )
    finally:
        windows.unhook()
        try:
            unload_cleanup(settings["cleanup_model"])
        except Exception as error:
            log.warning("unloading the cleanup model failed with %s", type(error).__name__)
    log.info("stdin closed, exiting")
    logging.shutdown()
    # Skips interpreter shutdown, which crashes if the models are still loading on their thread.
    os._exit(0)


def run_dictation(data_dir: Path, settings: dict, hotkey: Hotkey, lock, queued, startup) -> None:
    """Loads the models, then runs Dictations for as long as the Engine runs."""
    from localflow_engine import mic, windows

    def send_error(message: str) -> None:
        protocol.send({"type": "error", "message": message})

    def failed(message: str) -> None:
        startup.error, startup.state = message, "failed"
        send_error(message)
        protocol.send(dictate.state("idle"))  # Ends "Starting up…" or "Downloading…".

    def on_download() -> None:
        startup.state = "downloading"
        protocol.send(dictate.state("downloading"))

    device, mic_error = mic.pick(settings["microphone"])
    if mic_error:
        send_error(mic_error)
    if speech.gpu_mb() < speech.MIN_GPU_MB:
        log.error("no NVIDIA GPU with %d MiB", speech.MIN_GPU_MB)
        return failed(speech.UNSUPPORTED)
    try:
        models = load_speech(on_download)
    except Exception as error:
        log.error("loading Parakeet failed with %s", type(error).__name__)
        gpu = isinstance(error, speech.GpuUnavailable)
        return failed(speech.NO_GPU if gpu else speech.NO_SPEECH)
    if startup.state == "downloading":
        startup.state = "loading"
        protocol.send(dictate.state("idle"))  # Ends "Downloading speech model…".
    model = settings["cleanup_model"]
    warm_up_cleanup(model, send_error)

    db = history.open_history(data_dir / "history.db")
    microphone = mic.Mic(
        lambda value: protocol.send({"type": "level", "value": round(value, 2)}), device
    )
    parts = SimpleNamespace(
        start=microphone.start,
        stop=microphone.stop,
        transcribe=lambda audio: transcribe(models, audio),
        save_failed=lambda audio: write_wav(data_dir / "last-failed.wav", audio),
        clean=lambda transcript: clean(transcript, model, send_error),
        target_app=windows.target_app,
        save=lambda raw_text, clean_text, target_app, status: history.save(
            db, raw_text, clean_text, target_app, status
        ),
        paste=windows.paste,
        send=protocol.send,
    )
    startup.state = "ready"
    if startup.shown:
        protocol.send(dictate.state("idle"))  # Ends "Starting up…".
    log.info("ready: hold or double-tap %s; close stdin to quit", settings["hotkey"])
    while True:
        dictate.step(hotkey, lock, queued, parts, time.monotonic)
