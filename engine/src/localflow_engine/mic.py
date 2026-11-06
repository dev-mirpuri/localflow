"""The microphone: the system default, 16 kHz mono, opened for each Recording."""

from collections.abc import Callable

import numpy as np
import sounddevice

from localflow_engine.speech import RATE

BLOCK = RATE // 20  # A level about 20 times a second.
QUIET_DB, LOUD_DB = -60, -10


def level(block: np.ndarray) -> float:
    """0-1 for the Oval's bars: the block's loudness from QUIET_DB to LOUD_DB."""
    rms = float(np.sqrt(np.mean(np.square(block)))) + 1e-9
    return min(1.0, max(0.0, (20 * np.log10(rms) - QUIET_DB) / (LOUD_DB - QUIET_DB)))


class Mic:
    def __init__(self, on_level: Callable[[float], None]) -> None:
        self.on_level = on_level
        self.stream = None
        self.blocks: list[np.ndarray] = []

    def start(self) -> None:
        self.blocks = []
        self.stream = sounddevice.InputStream(
            samplerate=RATE, channels=1, dtype="float32", blocksize=BLOCK, callback=self._block
        )
        self.stream.start()

    def _block(self, data: np.ndarray, _frames, _time, _status) -> None:
        block = data[:, 0].copy()
        self.blocks.append(block)
        self.on_level(level(block))

    def stop(self) -> np.ndarray:
        """Closes the mic and returns the Recording as float32 samples."""
        if self.stream is not None:
            self.stream.close()
            self.stream = None
        return np.concatenate(self.blocks) if self.blocks else np.zeros(0, np.float32)
