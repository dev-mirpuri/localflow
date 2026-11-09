import logging
import queue
import threading
from types import SimpleNamespace

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
        self.sent: list[dict] = []

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

    def save(self, raw_text: str, clean_text: str, target_app: str, status: str) -> dict:
        self.calls.append("save")
        self.saved.append((raw_text, clean_text, target_app, status))
        return {"id": len(self.saved), "clean_text": clean_text}

    # The protocol
    def send(self, message: dict) -> None:
        self.sent.append(message)

    def states(self) -> list[str]:
        return [message["state"] for message in self.sent if message["type"] == "state"]

    def command(self, name: str, at: float) -> None:
        self.now = at
        dictate.on_command(self.hotkey, self.lock, self.queued, name, at)

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

    def failing_save(raw_text: str, clean_text: str, target_app: str, status: str) -> dict:
        raise OSError("disk full")

    fakes.save = failing_save
    fakes.key(CTRL, True, 10)
    fakes.key(CTRL, False, 11)
    fakes.step()
    assert fakes.pasted == ["Hello there. "]
    assert_next_press_records(fakes)


def test_push_to_talk_sends_listening_processing_the_result_then_idle():
    fakes = Fakes()
    fakes.key(CTRL, True, 10)
    fakes.step()
    fakes.key(CTRL, False, 11)
    fakes.step()
    assert fakes.sent == [
        {"type": "state", "state": "listening"},
        {"type": "state", "state": "processing"},
        {"type": "result", "entry": {"id": 1, "clean_text": "Hello there."}},
        {"type": "state", "state": "idle"},
    ]


def test_tap_wait_is_listening_and_a_double_tap_sends_handsfree():
    fakes = Fakes()
    fakes.key(CTRL, True, 10)
    fakes.key(CTRL, False, 10.05)
    fakes.step()
    assert fakes.states() == ["listening"]
    fakes.key(CTRL, True, 10.15)
    fakes.step()
    assert fakes.states() == ["listening", "handsfree"]


def test_the_finish_command_acts_like_the_tick_button_in_hands_free():
    fakes = Fakes()
    fakes.key(CTRL, True, 10)
    fakes.key(CTRL, False, 10.05)
    fakes.key(CTRL, True, 10.15)
    fakes.key(CTRL, False, 10.2)
    fakes.command("finish", 12)
    fakes.step()
    assert fakes.pasted == ["Hello there. "]
    assert fakes.states()[-2:] == ["processing", "idle"]


def test_the_cancel_command_acts_like_the_cross_button_in_hands_free():
    fakes = Fakes()
    fakes.key(CTRL, True, 10)
    fakes.key(CTRL, False, 10.05)
    fakes.key(CTRL, True, 10.15)
    fakes.key(CTRL, False, 10.2)
    fakes.command("cancel", 12)
    fakes.step()
    assert fakes.calls == ["mic start", "mic stop"]
    assert fakes.states() == ["listening", "handsfree", "idle"]


def test_a_discarded_tap_sends_idle():
    fakes = Fakes()
    fakes.key(CTRL, True, 10)
    fakes.key(CTRL, False, 10.05)
    fakes.step(at=10.5)
    assert fakes.states() == ["listening", "idle"]


def test_a_failed_transcription_sends_an_error_then_idle():
    fakes = Fakes()

    def failing_transcribe(audio: np.ndarray) -> str:
        raise RuntimeError("CUDA out of memory")

    fakes.transcribe = failing_transcribe
    fakes.key(CTRL, True, 10)
    fakes.key(CTRL, False, 11)
    fakes.step()
    assert [message["type"] for message in fakes.sent] == ["state", "state", "error", "state"]
    assert fakes.states()[-1] == "idle"


def test_states_bracket_the_mic_so_no_level_arrives_outside_listening():
    fakes = Fakes()
    mic_open_when_sent = []

    def send(message: dict) -> None:
        if message["type"] == "state":
            is_open = fakes.calls.count("mic start") > fakes.calls.count("mic stop")
            mic_open_when_sent.append((message["state"], is_open))

    fakes.send = send
    fakes.key(CTRL, True, 10)
    fakes.step()
    fakes.key(CTRL, False, 11)
    fakes.step()
    fakes.key(CTRL, True, 12)
    fakes.key(A, True, 12.5)
    fakes.step()
    assert mic_open_when_sent == [
        ("listening", False),
        ("processing", False),
        ("idle", False),
        ("listening", False),
        ("idle", False),
    ]


def test_an_unknown_command_is_refused_rather_than_cancelling():
    fakes = Fakes()
    fakes.key(CTRL, True, 10)
    fakes.key(CTRL, False, 10.05)
    fakes.key(CTRL, True, 10.15)
    with pytest.raises(ValueError):
        fakes.command("stop", 12)
    fakes.step()
    assert fakes.states() == ["listening", "handsfree"]


class Startup:
    """The models' loading, as run_dictate tracks it, and the keys held back meanwhile."""

    def __init__(self, state: str) -> None:
        self.startup = SimpleNamespace(state=state, held=False, shown=False)
        self.sent: list[dict] = []

    def key(self, key: tuple[str, int], down: bool, injected: bool = False) -> bool:
        name, _scan_code = key
        return dictate.held_back(self.startup, "right ctrl", name, down, injected, self.sent.append)


def test_a_press_while_loading_sends_loading_once_and_records_nothing():
    startup = Startup("loading")
    assert startup.key(CTRL, True) is True
    assert startup.key(CTRL, True) is True  # auto-repeat
    assert startup.key(CTRL, False) is True
    assert startup.sent == [{"type": "state", "state": "loading"}]
    assert startup.startup.shown


def test_a_press_while_downloading_records_nothing_and_sends_nothing():
    startup = Startup("downloading")
    assert startup.key(CTRL, True) is True
    assert startup.key(CTRL, False) is True
    assert startup.sent == []


def test_a_hotkey_held_through_warm_up_is_held_back_until_released():
    startup = Startup("loading")
    startup.key(CTRL, True)
    startup.startup.state = "ready"
    assert startup.key(CTRL, True) is True  # auto-repeat must not start a Recording
    assert startup.key(CTRL, False) is True
    assert startup.key(CTRL, True) is False
    assert startup.key(A, True) is False


def test_every_press_after_speech_failed_to_load_shows_its_error_and_records_nothing():
    startup = Startup("failed")
    startup.startup.error = "The GPU isn't available."
    for _ in range(2):
        assert startup.key(CTRL, True) is True
        assert startup.key(CTRL, True) is True  # auto-repeat
        assert startup.key(CTRL, False) is True
    error = {"type": "error", "message": "The GPU isn't available."}
    assert startup.sent == [error, error]


def test_a_mic_that_wont_open_shows_the_error_and_the_next_press_still_records():
    fakes = Fakes()

    def failing_start() -> None:
        fakes.calls.append("mic start")
        raise OSError("no default input device")

    fakes.start = failing_start
    fakes.key(CTRL, True, 10)
    fakes.step()
    fakes.key(CTRL, False, 11)
    fakes.step()
    assert fakes.sent == [
        dictate.state("listening"),
        {"type": "error", "message": dictate.NO_MIC},
        dictate.state("idle"),
    ]
    del fakes.start
    assert_next_press_records(fakes)
