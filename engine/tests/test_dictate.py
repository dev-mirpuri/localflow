import queue
import threading

import numpy as np

from localflow_engine import dictate
from localflow_engine.hotkey import Hotkey

CTRL = ("right ctrl", 29)
A = ("a", 30)
AUDIO = np.ones(16000, np.float32)


class Fakes:
    """The Engine's parts, faked, plus a clock the test moves by hand."""

    def __init__(self, cleaned: str = "Hello there.") -> None:
        self.hotkey = Hotkey("right ctrl")
        self.lock = threading.Lock()
        self.queued: queue.Queue = queue.Queue()
        self.now = 0.0
        self.calls: list[str] = []
        self.pasted: list[str] = []
        self.cleaned = cleaned

    def key(self, key: tuple[str, int], down: bool, at: float, injected: bool = False) -> bool:
        self.now = at
        name, scan_code = key
        return dictate.on_key(
            self.hotkey, self.lock, self.queued, name, scan_code, down, injected, at
        )

    def step(self, at: float | None = None) -> None:
        if at is not None:
            self.now = at
        dictate.step(
            self.hotkey,
            self.lock,
            self.queued,
            self,
            self.transcribe,
            self.clean,
            self.paste,
            lambda: self.now,
        )

    # The mic
    def start(self) -> None:
        self.calls.append("mic start")

    def stop(self) -> np.ndarray:
        self.calls.append("mic stop")
        return AUDIO

    def transcribe(self, audio: np.ndarray) -> str:
        assert audio is AUDIO
        self.calls.append("transcribe")
        return "hello there"

    def clean(self, transcript: str) -> tuple[str, str]:
        assert transcript == "hello there"
        self.calls.append("clean")
        return self.cleaned, "ok"

    def paste(self, text: str) -> None:
        self.calls.append("paste")
        self.pasted.append(text)


def test_push_to_talk_records_from_key_down_and_pastes_the_cleaned_text():
    fakes = Fakes()
    fakes.key(CTRL, True, 10)
    fakes.step()
    assert fakes.calls == ["mic start"]
    fakes.key(CTRL, False, 11)
    fakes.step()
    assert fakes.calls == ["mic start", "mic stop", "transcribe", "clean", "paste"]
    assert fakes.pasted == ["Hello there. "]


def test_the_next_press_after_a_paste_starts_a_new_recording():
    fakes = Fakes()
    fakes.key(CTRL, True, 10)
    fakes.key(CTRL, False, 11)
    fakes.step()
    fakes.step()
    fakes.calls.clear()
    fakes.key(CTRL, True, 12)
    fakes.step()
    assert fakes.calls == ["mic start"]


def test_another_key_during_push_to_talk_cancels_without_processing():
    fakes = Fakes()
    fakes.key(CTRL, True, 10)
    assert fakes.key(A, True, 10.5) is False
    fakes.step()
    fakes.key(CTRL, False, 11)
    fakes.step()
    assert fakes.calls == ["mic start", "mic stop"]


def test_esc_cancels_hands_free_and_is_swallowed():
    fakes = Fakes()
    fakes.key(CTRL, True, 10)
    fakes.key(CTRL, False, 10.05)
    fakes.key(CTRL, True, 10.15)
    fakes.key(CTRL, False, 10.2)
    assert fakes.key(("esc", 1), True, 12) is True
    fakes.step()
    fakes.step()
    assert fakes.calls == ["mic start", "mic stop"]


def test_a_single_tap_is_discarded_once_the_gap_passes():
    fakes = Fakes()
    fakes.key(CTRL, True, 10)
    fakes.key(CTRL, False, 10.05)
    fakes.step(at=10.3)
    assert fakes.calls == ["mic start"]
    fakes.step(at=10.5)
    assert fakes.calls == ["mic start", "mic stop"]


def test_a_recording_finishes_by_itself_after_3_minutes_and_is_pasted():
    fakes = Fakes()
    fakes.key(CTRL, True, 10)
    fakes.key(CTRL, False, 10.05)
    fakes.key(CTRL, True, 10.15)
    fakes.key(CTRL, False, 10.2)
    fakes.step(at=189.9)
    assert fakes.pasted == []
    fakes.step(at=190)
    assert fakes.pasted == ["Hello there. "]


def test_the_paste_waits_until_the_hotkey_is_physically_up():
    fakes = Fakes()
    fakes.key(CTRL, True, 10)
    fakes.key(CTRL, False, 10.05)
    fakes.key(CTRL, True, 10.15)
    fakes.key(CTRL, False, 10.2)
    fakes.key(CTRL, True, 12)  # Finishes Hands-free, and is still held.
    held_at_paste = []
    paste = fakes.paste

    def paste_noting_the_hotkey(text: str) -> None:
        held_at_paste.append("right ctrl" in fakes.hotkey.held)
        paste(text)

    fakes.paste = paste_noting_the_hotkey
    release = threading.Timer(0.1, fakes.key, (CTRL, False, 12.1))
    release.start()
    fakes.step()
    release.join()
    assert held_at_paste == [False]
    assert fakes.pasted == ["Hello there. "]


def test_trailing_whitespace_is_stripped_and_one_space_added_keeping_inner_line_breaks():
    fakes = Fakes(cleaned="My plan is:\n1. Clean the desk.\n2. Pay the rent.\n \n")
    fakes.key(CTRL, True, 10)
    fakes.key(CTRL, False, 11)
    fakes.step()
    assert fakes.pasted == ["My plan is:\n1. Clean the desk.\n2. Pay the rent. "]


def test_keys_sent_by_the_engine_itself_do_not_cancel_push_to_talk():
    fakes = Fakes()
    fakes.key(CTRL, True, 10)
    fakes.key(("ctrl", 29), True, 10.5, injected=True)
    fakes.key(("v", 47), True, 10.5, injected=True)
    fakes.key(CTRL, False, 11)
    fakes.step()
    assert fakes.pasted == ["Hello there. "]


def test_nothing_is_pasted_when_cleanup_leaves_no_text():
    fakes = Fakes(cleaned="")
    fakes.key(CTRL, True, 10)
    fakes.key(CTRL, False, 11)
    fakes.step()
    assert fakes.pasted == []
    fakes.calls.clear()
    fakes.key(CTRL, True, 12)
    fakes.step()
    assert fakes.calls == ["mic start"]
