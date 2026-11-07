from types import SimpleNamespace

import numpy as np
import pytest

from localflow_engine.speech import RATE, transcribe


class FakeModel:
    def __init__(self, result: object) -> None:
        self.result = result

    def recognize(self, audio: np.ndarray, sample_rate: int) -> object:
        return self.result


@pytest.mark.parametrize(
    ("seconds", "transcript"),
    [
        (19.9, "straight"),
        (20.0, "straight"),
        (20.1, "first second"),
    ],
)
def test_only_recordings_over_20_seconds_go_through_vad(seconds: float, transcript: str) -> None:
    parakeet = FakeModel("straight")
    parakeet_with_vad = FakeModel([SimpleNamespace(text="first"), SimpleNamespace(text="second")])
    audio = np.zeros(int(seconds * RATE), np.float32)

    assert transcribe((parakeet, parakeet_with_vad), audio) == transcript
