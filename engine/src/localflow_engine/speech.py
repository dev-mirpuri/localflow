"""Speech recognition: Parakeet on the GPU, with Silero VAD first for long Recordings."""

import contextlib
import sys
import time
import wave
from pathlib import Path

import numpy as np
import onnx_asr
import onnxruntime as ort

MODEL = "nemo-parakeet-tdt-0.6b-v2"
RATE = 16000
VAD_OVER_S = 20


def read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path)) as w:
        if (w.getnchannels(), w.getsampwidth(), w.getframerate()) != (1, 2, RATE):
            raise ValueError(f"{path} must be 16 kHz, mono, 16-bit")
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768


def load_speech() -> tuple:
    """Loads Parakeet and warms it up. Returns it plain and with VAD, for transcribe()."""
    ort.set_default_logger_severity(3)
    with contextlib.redirect_stdout(sys.stderr):  # preload_dlls() prints its problems
        ort.preload_dlls()
    start = time.perf_counter()
    # kSameAsRequested: about 560 MB less VRAM than ORT's default arena, at the same speed.
    cuda = ("CUDAExecutionProvider", {"arena_extend_strategy": "kSameAsRequested"})
    parakeet = onnx_asr.load_model(MODEL, providers=[cuda])
    # ORT falls back to the CPU silently, and onnx-asr has no public way to ask.
    used = parakeet.asr._encoder.get_providers()[0]  # pyright: ignore[reportAttributeAccessIssue]
    if used != "CUDAExecutionProvider":
        raise RuntimeError(f"Parakeet is not on CUDA, it is on {used}")
    vad = onnx_asr.load_vad("silero", providers=["CPUExecutionProvider"])
    print(f"load: {time.perf_counter() - start:.2f} s", file=sys.stderr)

    start = time.perf_counter()
    parakeet.recognize(np.zeros(RATE, np.float32), sample_rate=RATE)
    print(f"warm-up: {time.perf_counter() - start:.2f} s", file=sys.stderr)
    return parakeet, parakeet.with_vad(vad, batch_size=1)


def transcribe(speech: tuple, audio: np.ndarray) -> str:
    """Returns the Transcript of 16 kHz mono float32 audio."""
    parakeet, parakeet_with_vad = speech
    if len(audio) > VAD_OVER_S * RATE:
        segments = parakeet_with_vad.recognize(audio, sample_rate=RATE)
        return " ".join(segment.text for segment in segments)
    return parakeet.recognize(audio, sample_rate=RATE)
