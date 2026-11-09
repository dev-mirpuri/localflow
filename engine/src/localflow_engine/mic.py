"""The microphone: picked by name from config.json, 16 kHz mono, opened for each Recording."""

import logging
from collections.abc import Callable

import numpy as np
import sounddevice

# dictate stays importable without sounddevice, which is Windows-only, so NO_MIC lives there.
from localflow_engine.dictate import NO_MIC
from localflow_engine.speech import RATE

BLOCK = RATE // 20  # A level about 20 times a second.
QUIET_DB, LOUD_DB = -60, -10
NOT_FOUND = "Microphone not found. Copy a name from engine.log into config.json."

log = logging.getLogger(__name__)


def pick(name: str) -> tuple[int | None, str | None]:
    """Logs the input devices. Returns the first whose name contains name, ignoring case,
    or None for the system default, and any Oval error."""
    try:
        devices = sounddevice.query_devices()
        # The default host API (MME) resamples to 16 kHz; WASAPI and WDM-KS may refuse it.
        inputs = [
            d
            for d in devices
            if d["max_input_channels"] > 0 and d["hostapi"] == sounddevice.default.hostapi
        ]
    except Exception as error:  # Each press reports it again if the mic won't open.
        log.error("listing input devices failed with %s", type(error).__name__)
        inputs = []
    for device in inputs:
        log.info("input device: %s", device["name"])
    if not inputs:
        return None, NO_MIC
    if not name:
        return None, None
    found = [d["index"] for d in inputs if name.casefold() in d["name"].casefold()]
    return (found[0], None) if found else (None, NOT_FOUND)


def level(block: np.ndarray) -> float:
    """0-1 for the Oval's bars: the block's loudness from QUIET_DB to LOUD_DB."""
    rms = float(np.sqrt(np.mean(np.square(block)))) + 1e-9
    return min(1.0, max(0.0, (20 * np.log10(rms) - QUIET_DB) / (LOUD_DB - QUIET_DB)))


class Mic:
    def __init__(self, on_level: Callable[[float], None], device: int | None) -> None:
        self.on_level = on_level
        self.device = device
        self.stream = None
        self.blocks: list[np.ndarray] = []

    def start(self) -> None:
        self.blocks = []
        self.stream = sounddevice.InputStream(
            samplerate=RATE,
            channels=1,
            dtype="float32",
            blocksize=BLOCK,
            device=self.device,
            callback=self._block,
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
