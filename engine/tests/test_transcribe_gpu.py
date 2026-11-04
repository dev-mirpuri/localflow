import subprocess
import wave
from pathlib import Path

import pytest

AUDIO = Path(__file__).resolve().parents[2] / "eval" / "audio"

pytestmark = pytest.mark.gpu


def run_transcribe(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["localflow-engine", "transcribe", str(path)],
        capture_output=True,
        encoding="utf-8",
        check=True,
    )


def test_prints_transcript_to_stdout_and_timings_to_stderr() -> None:
    result = run_transcribe(AUDIO / "01.wav")

    assert result.stdout.strip() == (
        "I looked over the proposal this morning and it seems fine to me."
    )
    assert "warm-up" in result.stderr
    assert "transcribe" in result.stderr
    assert "proposal" not in result.stderr


def test_transcribes_a_recording_over_20_seconds(tmp_path: Path) -> None:
    long_wav = tmp_path / "long.wav"
    with wave.open(str(long_wav), "wb") as out:
        for clip in ["01", "02", "03", "04", "05"]:
            with wave.open(str(AUDIO / f"{clip}.wav")) as w:
                if clip == "01":
                    out.setparams(w.getparams())
                out.writeframes(w.readframes(w.getnframes()))
    with wave.open(str(long_wav)) as w:
        assert w.getnframes() / w.getframerate() > 20

    result = run_transcribe(long_wav)

    assert "proposal this morning" in result.stdout
    assert "check the numbers" in result.stdout
    assert "\n" not in result.stdout.strip()
