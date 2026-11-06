"""Dictation: the Hotkey's actions drive the mic, speech, cleanup and paste, passed in as arguments.

The hook thread calls key() and only updates state; the main thread calls step() in a loop.
"""

import queue
import sys
import threading
import time
from collections.abc import Callable

from localflow_engine.hotkey import Hotkey

WAIT_S = 0.01
KEY_UP_POLL_S = 0.005


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


def step(
    hotkey: Hotkey,
    lock: threading.Lock,
    queued: queue.Queue,
    mic,
    transcribe: Callable,
    clean: Callable,
    paste: Callable,
    now: Callable[[], float],
) -> None:
    """One turn of the main loop: waits briefly for the hook's actions, ticks, and acts on them."""
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
        print(f"dictate: {action:<20}", file=sys.stderr)
        if action == "start":
            mic.start()
        elif action in ("cancel", "discard"):
            mic.stop()
        elif action == "finish":
            started = time.perf_counter()
            text, status = clean(transcribe(mic.stop()))
            if text.strip():
                while hotkey.name in hotkey.held:  # Ctrl+V must not combine with the Hotkey.
                    time.sleep(KEY_UP_POLL_S)
                paste(text.rstrip() + " ")
            took = time.perf_counter() - started
            print(f"dictate: done {took:.2f} s after finish, {status}", file=sys.stderr)
            with lock:
                hotkey.done()
