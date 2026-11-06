import argparse
import queue
import sys
import threading
import time
import wave
from pathlib import Path

from localflow_engine import dictate
from localflow_engine.cleanup import clean, warm_up_cleanup
from localflow_engine.hotkey import Hotkey
from localflow_engine.speech import load_speech, read_wav, transcribe

HOTKEY = "right ctrl"  # Until T9 adds config.


def main() -> None:
    parser = argparse.ArgumentParser(prog="localflow-engine")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("transcribe").add_argument("wav", type=Path)
    commands.add_parser("dictate")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")  # pyright: ignore[reportAttributeAccessIssue]
    if args.command == "dictate":
        run_dictate()
    else:
        run_transcribe(args.wav)


def run_transcribe(path: Path) -> None:
    try:
        audio = read_wav(path)
    except (OSError, EOFError, wave.Error, ValueError) as error:
        sys.exit(f"Can't read {path}: {error}")

    speech = load_speech()
    start = time.perf_counter()
    transcript = transcribe(speech, audio)
    print(f"transcribe: {time.perf_counter() - start:.2f} s", file=sys.stderr)
    print(transcript)


def run_dictate() -> None:
    # Imported here because these are Windows-only; see pyproject.toml.
    from localflow_engine import windows
    from localflow_engine.mic import Mic

    speech = load_speech()
    try:
        warm_up_cleanup()
    except Exception as error:  # Cleanup falls back to the Transcript on its own.
        print(f"cleanup: warm-up failed with {type(error).__name__}", file=sys.stderr)

    hotkey, lock, queued = Hotkey(HOTKEY), threading.Lock(), queue.Queue()
    mic = Mic(lambda value: print(f"{'#' * round(value * 20):20}", end="\r", file=sys.stderr))
    windows.hook(
        lambda name, scan_code, down, injected: dictate.on_key(
            hotkey, lock, queued, name, scan_code, down, injected, time.monotonic()
        )
    )
    print("Ready: hold or double-tap Right Ctrl, Ctrl+C to quit", file=sys.stderr)
    try:
        while True:
            dictate.step(
                hotkey,
                lock,
                queued,
                mic,
                lambda audio: transcribe(speech, audio),
                clean,
                windows.paste,
                time.monotonic,
            )
    except KeyboardInterrupt:
        windows.unhook()
