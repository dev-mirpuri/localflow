"""Dictation: the Hotkey's actions drive the mic, speech, cleanup and paste, passed in as arguments.

The hook thread calls key() and only updates state; the main thread calls step() in a loop.
"""

import logging
import queue
import threading
import time
from collections.abc import Callable

import numpy as np

from localflow_engine.hotkey import Hotkey
from localflow_engine.speech import RATE

log = logging.getLogger(__name__)

WAIT_S = 0.01
KEY_UP_POLL_S = 0.005
MIN_S = 0.3
# Room noise in the eval clips is about -49 dBFS; their quietest speech peaks at -33.
SILENT_DBFS = -42
LOUDNESS_BLOCK = RATE // 20
NO_MIC = "No microphone found. Plug one in, or fix its name in config.json."
NOT_TRANSCRIBED = "Couldn't transcribe that, so it's kept in last-failed.wav. Try again."


def worth_transcribing(audio: np.ndarray) -> bool:
    """False for a Recording under MIN_S, or with no 50 ms block louder than SILENT_DBFS."""
    if len(audio) < MIN_S * RATE:
        return False
    blocks = audio[: len(audio) // LOUDNESS_BLOCK * LOUDNESS_BLOCK].reshape(-1, LOUDNESS_BLOCK)
    loudest = float(np.sqrt(np.mean(np.square(blocks), axis=1)).max())
    return 20 * np.log10(loudest + 1e-9) > SILENT_DBFS


def state(name: str) -> dict:
    """A protocol state message. The mic is closed whenever one other than "listening" goes out."""
    return {"type": "state", "state": name}


def held_back(startup, hotkey_name: str, name: str, down: bool, injected: bool, send) -> bool:
    """Whether a key skips the Hotkey: while the models load, and until a press meanwhile is up.

    startup has the loading state ("downloading", "loading", "ready" or "failed"), held, and
    shown, which is set once "loading" is sent. A press while downloading sends nothing, and
    each press once failed sends startup.error.
    """
    if startup.state == "ready" and not startup.held:
        return False
    if name == hotkey_name and not injected:
        if down and not startup.held and startup.state == "loading":
            startup.shown = True
            send(state("loading"))
        elif down and not startup.held and startup.state == "failed":
            send({"type": "error", "message": startup.error})
        startup.held = down
    return True


def on_key(
    hotkey: Hotkey,
    lock: threading.Lock,
    queued: queue.Queue,
    name: str,
    scan_code: int,
    down: bool,
    injected: bool,
    now: float,
) -> bool:
    """Feeds a key event from the hook thread. Returns whether to swallow it."""
    with lock:
        actions, swallow = hotkey.key(name, scan_code, down, now, injected)
    if actions:
        queued.put(actions)
    return swallow


def on_command(
    hotkey: Hotkey, lock: threading.Lock, queued: queue.Queue, name: str, now: float
) -> None:
    """The App's "finish" and "cancel" commands: the Oval's ✓ and ✕."""
    if name not in ("finish", "cancel"):
        raise ValueError("unknown command")
    with lock:
        actions = hotkey.finish(now) if name == "finish" else hotkey.cancel(now)
    if actions:
        queued.put(actions)


def step(
    hotkey: Hotkey,
    lock: threading.Lock,
    queued: queue.Queue,
    parts,
    now: Callable[[], float],
) -> None:
    """One turn of the main loop: waits briefly for the hook's actions, ticks, and acts on them.

    parts has the mic's start() and stop(), transcribe, save_failed, clean, target_app, save,
    paste, and send for protocol messages.
    """
    actions = []
    try:  # Bounded: on Windows a get() with no timeout can't be interrupted by Ctrl+C.
        actions += queued.get(timeout=WAIT_S)
        while True:
            actions += queued.get_nowait()
    except queue.Empty:
        pass
    with lock:
        actions += hotkey.tick(now())
    for action in actions:
        log.info(action)
        if action == "start":
            parts.send(state("listening"))
            try:
                parts.start()
            except Exception as error:  # The rest of this batch belonged to that Recording.
                log.error("the mic failed to open with %s", type(error).__name__)
                parts.stop()
                with lock:
                    hotkey.done()
                parts.send({"type": "error", "message": NO_MIC})
                parts.send(state("idle"))
                return
        elif action == "hands_free":
            parts.send(state("handsfree"))
        elif action in ("cancel", "discard"):
            parts.stop()
            parts.send(state("idle"))
        elif action == "finish":
            try:
                finish(hotkey, parts)
            finally:
                with lock:
                    hotkey.done()
                parts.send(state("idle"))


def finish(hotkey: Hotkey, parts) -> None:
    """Transcribes, cleans, saves and pastes a finished Recording."""
    started = time.perf_counter()
    audio = parts.stop()
    parts.send(state("processing"))
    if not worth_transcribing(audio):
        log.info("discarded a short or silent Recording")
        return
    try:
        transcript = parts.transcribe(audio)
    except Exception as error:
        log.error("transcription failed with %s", type(error).__name__)
        parts.save_failed(audio)
        parts.send({"type": "error", "message": NOT_TRANSCRIBED})
        return
    text, status = parts.clean(transcript)
    text = text.rstrip()
    if not text:
        log.info("discarded a Transcript of only filler")
        return
    while hotkey.name in hotkey.held:  # Ctrl+V must not combine with the Hotkey.
        time.sleep(KEY_UP_POLL_S)
    try:
        entry = parts.save(transcript, text, parts.target_app(), status)
        parts.send({"type": "result", "entry": entry})
    except Exception as error:  # Paste anyway: the words still reach the Target app.
        log.error("saving the Entry failed with %s", type(error).__name__)
    try:
        parts.paste(text + " ")
    except Exception as error:  # The Entry is saved, so the words are in History.
        log.error("paste failed with %s", type(error).__name__)
    took = time.perf_counter() - started
    log.info("release-to-text %.2f s, %s", took, status)
