import argparse
import sys
import time
import wave
from pathlib import Path

from localflow_engine.speech import load_speech, read_wav, transcribe


def main() -> None:
    parser = argparse.ArgumentParser(prog="localflow-engine")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("transcribe").add_argument("wav", type=Path)
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")  # pyright: ignore[reportAttributeAccessIssue]
    try:
        audio = read_wav(args.wav)
    except (OSError, EOFError, wave.Error, ValueError) as error:
        sys.exit(f"Can't read {args.wav}: {error}")

    speech = load_speech()
    start = time.perf_counter()
    transcript = transcribe(speech, audio)
    print(f"transcribe: {time.perf_counter() - start:.2f} s", file=sys.stderr)
    print(transcript)
