import logging
import queue
import threading

import numpy as np
import pytest

from localflow_engine import dictate
from localflow_engine.hotkey import Hotkey

CTRL = ("right ctrl", 29)
A = ("a", 30)
AUDIO = np.ones(16000, np.float32)


class Fakes:
    """The Engine's parts, faked, plus a clock the test moves by hand."""

    def __init__(self, cleaned: str = "Hello there.", audio: np.ndarray = AUDIO) -> None:
        self.audio = audio
        self.hotkey = Hotkey("right ctrl")
        self.lock = threading.Lock()
        self.queued: queue.Queue = queue.Queue()
        self.now = 0.0
        self.calls: list[str] = []
        self.pasted: list[str] = []
        self.saved: list[tuple[str, str, str, str]] = []
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
            lambda: self.now,
        )

    # The mic
    def start(self) -> None:
        self.calls.append("mic start")

    def stop(self) -> np.ndarray:
        self.calls.append("mic stop")
        return self.audio

    def transcribe(self, audio: np.ndarray) -> str:
        assert audio is self.audio
        self.calls.append("transcribe")
        return "hello there"

    def clean(self, transcript: str) -> tuple[str, str]:
        assert transcript == "hello there"
        self.calls.append("clean")
        return self.cleaned, "ok"

    def save_failed(self, audio: np.ndarray) -> None:
        assert audio is self.audio
        self.calls.append("save failed")

    def target_app(self) -> str:
        self.calls.append("target app")
        return "notepad.exe"

    def save(self, raw_text: str, clean_text: str, target_app: str, status: str) -> None:
        self.calls.append("save")
        self.saved.append((raw_text, clean_text, target_app, status))

    def paste(self, text: str) -> None:
        self.calls.append("paste")
        self.pasted.append(text)


def assert_next_press_records(fakes: Fakes) -> None:
    fakes.calls.clear()
    fakes.key(CTRL, True, 12)
    fakes.step()
    assert fakes.calls == ["mic start"]


def test_push_to_talk_records_from_key_down_and_saves_the_entry_before_pasting():
    fakes = Fakes()
    fakes.key(CTRL, True, 10)
    fakes.step()
    assert fakes.calls == ["mic start"]
    fakes.key(CTRL, False, 11)
    fakes.step()
    assert fakes.calls == [
        "mic start",
        *["mic stop", "transcribe", "clean", "target app", "save", "paste"],
    ]
    assert fakes.saved == [("hello there", "Hello there.", "notepad.exe", "ok")]
    assert fakes.pasted == ["Hello there. "]


def test_the_next_press_after_a_paste_starts_a_new_recording():
    fakes = Fakes()
    fakes.key(CTRL, True, 10)
    fakes.key(CTRL, False, 11)
    fakes.step()
    fakes.step()
    assert_next_press_records(fakes)


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


def test_the_target_app_and_paste_wait_until_the_hotkey_is_physically_up():
    fakes = Fakes()
    fakes.key(CTRL, True, 10)
    fakes.key(CTRL, False, 10.05)
    fakes.key(CTRL, True, 10.15)
    fakes.key(CTRL, False, 10.2)
    fakes.key(CTRL, True, 12)  # Finishes Hands-free, and is still held.
    held_at = []
    target_app = fakes.target_app

    def target_app_noting_the_hotkey() -> str:
        held_at.append("right ctrl" in fakes.hotkey.held)
        return target_app()

    fakes.target_app = target_app_noting_the_hotkey
    release = threading.Timer(0.1, fakes.key, (CTRL, False, 12.1))
    release.start()
    fakes.step()
    release.join()
    assert held_at == [False]
    assert fakes.calls[-3:] == ["target app", "save", "paste"]


def test_trailing_whitespace_is_stripped_and_one_space_added_keeping_inner_line_breaks():
    fakes = Fakes(cleaned="My plan is:\n1. Clean the desk.\n2. Pay the rent.\n \n")
    fakes.key(CTRL, True, 10)
    fakes.key(CTRL, False, 11)
    fakes.step()
    assert fakes.pasted == ["My plan is:\n1. Clean the desk.\n2. Pay the rent. "]
    assert fakes.saved[0][1] == "My plan is:\n1. Clean the desk.\n2. Pay the rent."


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
    assert fakes.saved == []
    assert_next_press_records(fakes)


def test_a_failed_paste_leaves_the_entry_saved_and_the_next_press_still_records():
    fakes = Fakes()

    def failing_paste(text: str) -> None:
        raise OSError("clipboard stayed busy for 1 s")

    fakes.paste = failing_paste
    fakes.key(CTRL, True, 10)
    fakes.key(CTRL, False, 11)
    fakes.step()
    assert fakes.saved == [("hello there", "Hello there.", "notepad.exe", "ok")]
    assert_next_press_records(fakes)


def test_a_failed_transcription_keeps_the_audio_and_saves_no_entry():
    fakes = Fakes()

    def failing_transcribe(audio: np.ndarray) -> str:
        fakes.calls.append("transcribe")
        raise RuntimeError("CUDA out of memory")

    fakes.transcribe = failing_transcribe
    fakes.key(CTRL, True, 10)
    fakes.key(CTRL, False, 11)
    fakes.step()
    assert fakes.calls == ["mic start", "mic stop", "transcribe", "save failed"]
    assert fakes.saved == []
    assert_next_press_records(fakes)


def tone(seconds: float, dbfs: float) -> np.ndarray:
    """A sine whose RMS is dbfs."""
    t = np.arange(int(seconds * 16000)) / 16000
    return (np.sqrt(2) * 10 ** (dbfs / 20) * np.sin(2 * np.pi * 200 * t)).astype(np.float32)


@pytest.mark.parametrize(
    ("audio", "processed"),
    [
        (tone(0.29, -20), False),
        (tone(0.31, -20), True),
        (np.zeros(16000, np.float32), False),
        (tone(2, -46), False),  # Room noise.
        (tone(2, -38), True),  # Quiet speech.
        (np.concatenate([tone(2, -46), tone(0.1, -30)]), True),  # One word in a long pause.
    ],
)
def test_short_or_silent_recordings_are_discarded_without_calling_the_models(audio, processed):
    fakes = Fakes(audio=audio)
    fakes.key(CTRL, True, 10)
    fakes.key(CTRL, False, 11)
    fakes.step()
    assert ("transcribe" in fakes.calls) is processed
    assert len(fakes.saved) == processed
    assert_next_press_records(fakes)


def test_logs_hold_the_release_to_text_timing_and_error_types_but_never_the_words(caplog):
    caplog.set_level(logging.DEBUG)
    fakes = Fakes()

    def failing_paste(text: str) -> None:
        raise OSError(f"could not paste {text}")

    fakes.paste = failing_paste
    fakes.key(CTRL, True, 10)
    fakes.key(CTRL, False, 11)
    fakes.step()
    assert "release-to-text" in caplog.text
    assert "OSError" in caplog.text
    assert "hello" not in caplog.text.lower()


def test_a_failed_save_still_pastes_the_text_and_the_next_press_still_records():
    fakes = Fakes()

    def failing_save(raw_text: str, clean_text: str, target_app: str, status: str) -> None:
        raise OSError("disk full")

    fakes.save = failing_save
    fakes.key(CTRL, True, 10)
    fakes.key(CTRL, False, 11)
    fakes.step()
    assert fakes.pasted == ["Hello there. "]
    assert_next_press_records(fakes)
