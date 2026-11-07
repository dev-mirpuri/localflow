"""Speech recognition: Parakeet on the GPU, with Silero VAD first for long Recordings."""

import contextlib
import logging
import sys
import time
import wave
from collections.abc import Callable
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)

MODEL = "nemo-parakeet-tdt-0.6b-v2"
REPO = "istupakov/parakeet-tdt-0.6b-v2-onnx"  # Where onnx-asr downloads MODEL from.
RATE = 16000
VAD_OVER_S = 20


def read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path)) as w:
        if (w.getnchannels(), w.getsampwidth(), w.getframerate()) != (1, 2, RATE):
            raise ValueError(f"{path} must be 16 kHz, mono, 16-bit")
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768


def write_wav(path: Path, audio: np.ndarray) -> None:
    """Writes float32 audio as the 16 kHz, mono, 16-bit WAV that read_wav() reads."""
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())


def load_speech(on_download: Callable[[], None] = lambda: None) -> tuple:
    """Loads Parakeet and warms it up. Returns it plain and with VAD, for transcribe().

    Calls on_download() first if Parakeet has to be downloaded.
    """
    # Imported here because these packages are Windows-only; see pyproject.toml.
    import onnx_asr
    import onnxruntime as ort
    from huggingface_hub import try_to_load_from_cache

    if not isinstance(try_to_load_from_cache(REPO, "encoder-model.onnx.data"), str):
        on_download()

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
    log.info("load %.2f s", time.perf_counter() - start)

    start = time.perf_counter()
    parakeet.recognize(np.zeros(RATE, np.float32), sample_rate=RATE)
    log.info("warm-up %.2f s", time.perf_counter() - start)
    return parakeet, parakeet.with_vad(vad, batch_size=1)


def transcribe(speech: tuple, audio: np.ndarray) -> str:
    """Returns the Transcript of 16 kHz mono float32 audio."""
    parakeet, parakeet_with_vad = speech
    if len(audio) > VAD_OVER_S * RATE:
        segments = parakeet_with_vad.recognize(audio, sample_rate=RATE)
        return " ".join(segment.text for segment in segments)
    return parakeet.recognize(audio, sample_rate=RATE)
