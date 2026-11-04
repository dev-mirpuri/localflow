import re
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

import httpx
import ollama
import pytest

from localflow_engine.cleanup import clean


class FakeModel:
    """Stands in for ollama.Client, the only thing faked. Echoes unless given a reply."""

    def __init__(self) -> None:
        self.reply: Callable[[str], str] = lambda text: text
        self.calls: list[dict] = []
        self.timeout = None

    def __call__(self, timeout: float) -> "FakeModel":
        self.timeout = timeout
        return self

    def chat(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append({"timeout": self.timeout, **kwargs})
        content = self.reply(sent_text(self.calls[-1]))
        return SimpleNamespace(message=SimpleNamespace(content=content))

    @property
    def sent(self) -> list[str]:
        return [sent_text(call) for call in self.calls]


def sent_text(call: dict) -> str:
    match = re.fullmatch(r"<transcript>(.*)</transcript>", call["messages"][-1]["content"], re.S)
    assert match
    return match[1]


@pytest.fixture
def model(monkeypatch: pytest.MonkeyPatch) -> FakeModel:
    fake = FakeModel()
    monkeypatch.setattr(ollama, "Client", fake)
    return fake


@pytest.mark.parametrize(
    "transcript",
    ["", "Um.", "um", "Uh, um, erm.", "Um. Uh.", "UH, er."],
)
def test_nothing_left_after_the_pre_pass_returns_empty_text(
    model: FakeModel, transcript: str
) -> None:
    assert clean(transcript) == ("", "ok")
    assert model.calls == []


@pytest.mark.parametrize(
    ("transcript", "cleaned"),
    [
        ("Um, okay then.", "Okay then."),
        ("okay then", "Okay then"),
        ("Um. Okay then.", "Okay then."),
        ("Okay then, um.", "Okay then."),
        ("Okay um then?", "Okay then?"),
        ("Um, the ER.", "The ER."),
        ("Sounds good", "Sounds good"),
        ("Really?!", "Really?!"),
    ],
)
def test_three_words_or_fewer_skip_the_model_and_capitalise(
    model: FakeModel, transcript: str, cleaned: str
) -> None:
    assert clean(transcript) == (cleaned, "ok")
    assert model.calls == []


def test_the_pre_pass_runs_before_the_three_word_check(model: FakeModel) -> None:
    clean("Um, uh, erm, one two three.")
    assert model.calls == []

    clean("Um, one two three four.")
    assert model.sent == ["one two three four."]


@pytest.mark.parametrize(
    ("transcript", "sent"),
    [
        ("UM, take the Uh, road ERM, north.", "take the road north."),
        ("We went to the ER and er waited there.", "We went to the ER and waited there."),
        ("The Er key is not an erm key.", "The Er key is not an key."),
        (
            "Under the umbrella, the Uhura era erupted.",
            "Under the umbrella, the Uhura era erupted.",
        ),
        ("It was um-hmm and er-hem and uh's today.", "It was um-hmm and er-hem and uh's today."),
    ],
)
def test_the_pre_pass_deletes_only_standalone_filler(
    model: FakeModel, transcript: str, sent: str
) -> None:
    clean(transcript)
    assert model.sent == [sent]


def adr_blocks() -> list[str]:
    adr = Path(__file__).resolve().parents[2] / "docs/adr/0001-s1-speech-and-cleanup-models.md"
    return re.findall(r"```text\n(.*?)\n```", adr.read_text(encoding="utf-8"), re.S)


def test_the_prompt_matches_adr_0001_word_for_word(model: FakeModel) -> None:
    system, examples = adr_blocks()
    turns = []
    for example in examples.split("\n\n"):
        user, assistant = example.split("\nAssistant: ")
        turns.append({"role": "user", "content": f"<transcript>{user[6:]}</transcript>"})
        turns.append({"role": "assistant", "content": assistant})

    clean("The real transcript goes last.")

    assert model.calls[0]["messages"] == [
        {"role": "system", "content": f"{system}\n/no_think"},
        *turns,
        {"role": "user", "content": "<transcript>The real transcript goes last.</transcript>"},
    ]


def test_the_model_is_called_with_the_fixed_settings(model: FakeModel) -> None:
    clean("The real transcript goes last.")

    call = model.calls[0]
    assert call["model"] == "qwen3:1.7b"
    assert call["think"] is False
    assert call["keep_alive"] == -1
    assert call["options"] == {"temperature": 0, "seed": 0}


TEN_WORDS = "one two three four five six seven eight nine ten."


@pytest.mark.parametrize(
    ("output", "accepted"),
    [
        ("one two three four five six", True),  # exactly 0.60x
        ("one two three four five", False),  # 0.50x
        (TEN_WORDS + " one two three", True),  # exactly 1.3x
        (TEN_WORDS + " one two three four", False),  # 1.4x
        ("one two three four five six seven eight new words", True),  # exactly 80% known
        ("one two three four five six seven new words here", False),  # 70% known
        ("ONE, two: Three four five six", True),  # case and punctuation don't count
        ("1. one two\n2. three four\n3. five six", True),  # all known once numbers are ignored
        ("one two three 4 5 6 7", False),  # numbers inside a line are ordinary words
        ("", False),
    ],
)
def test_output_is_rejected_on_overlap_or_length(
    model: FakeModel, output: str, accepted: bool
) -> None:
    model.reply = lambda text: output

    expected = (output, "ok") if accepted else (TEN_WORDS, "raw_fallback")
    assert clean(TEN_WORDS) == expected


def test_overlap_and_length_are_measured_against_the_text_sent_to_the_model(
    model: FakeModel,
) -> None:
    # 5 words sent; the Transcript's 9 would make this 3-word output under 0.60x.
    model.reply = lambda text: "one two three"

    assert clean("Um, um, um, um, one two three four five.") == ("one two three", "ok")


def raises(error: Exception) -> Callable[[str], str]:
    def reply(text: str) -> str:
        raise error

    return reply


@pytest.mark.parametrize(
    "error",
    [
        httpx.ReadTimeout("timed out"),
        httpx.ConnectError("Ollama isn't running"),
        ConnectionError("Ollama isn't running"),
        ollama.ResponseError("model not found"),
    ],
)
def test_an_error_or_timeout_falls_back_to_the_transcript(
    model: FakeModel, error: Exception
) -> None:
    model.reply = raises(error)
    transcript = "Um, so the raw words are kept."

    assert clean(transcript) == (transcript, "raw_fallback")


def test_a_failure_logs_its_type_but_never_the_words(
    model: FakeModel, capsys: pytest.CaptureFixture[str]
) -> None:
    model.reply = raises(httpx.ReadTimeout("private words"))

    clean("Some private words go here.")

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "ReadTimeout" in captured.err
    assert "private" not in captured.err


def test_a_rejection_logs_nothing_of_the_words(
    model: FakeModel, capsys: pytest.CaptureFixture[str]
) -> None:
    model.reply = lambda text: "banana"

    clean("Some private words go here.")

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "reject" in captured.err
    assert "private" not in captured.err
    assert "banana" not in captured.err


def sentence(count: int, word: str = "word") -> str:
    return " ".join([word] * count) + "."


@pytest.mark.parametrize(
    ("sizes", "chunk_sizes"),
    [
        ([20, 20], [40]),  # exactly the limit stays together
        ([20, 21], [20, 21]),  # one word over starts a new chunk
        ([20, 20, 20], [40, 20]),
        ([50], [50]),  # a long sentence is never split
        ([10, 50, 10], [10, 50, 10]),
    ],
)
def test_chunks_group_whole_sentences_up_to_40_words(
    model: FakeModel, sizes: list[int], chunk_sizes: list[int]
) -> None:
    clean(" ".join(sentence(size) for size in sizes))

    assert [len(text.split()) for text in model.sent] == chunk_sizes


def test_a_sentence_under_4_words_stays_attached_to_the_next_one(model: FakeModel) -> None:
    # "Sorry." would fit in the first chunk, but it belongs with what it introduces.
    first = sentence(38)
    second = "Sorry. I meant. Sarah is on the call."

    clean(f"{first} {second}")

    assert model.sent == [first, second]


def test_a_sentence_of_exactly_4_words_stands_alone(model: FakeModel) -> None:
    four = sentence(4, "four")
    next_one = sentence(38)

    clean(f"{four} {next_one}")

    assert model.sent == [four, next_one]  # attached, they'd be one 42-word chunk


def test_question_and_exclamation_marks_end_sentences_too(model: FakeModel) -> None:
    first = " ".join(["word"] * 38) + "?"
    second = " ".join(["other"] * 38) + "!"

    clean(f"{first} {second}")

    assert model.sent == [first, second]


def test_chunks_are_pre_passed_and_joined_with_a_space(model: FakeModel) -> None:
    first = sentence(38)
    second = sentence(38, "other")

    assert clean(f"Um, {first} Uh, {second}") == (f"{first} {second}", "ok")
    assert model.sent == [first, second]


def test_a_chunk_the_pre_pass_empties_is_dropped_without_a_fallback(model: FakeModel) -> None:
    first = sentence(40)

    assert clean(f"{first} Um.") == (first, "ok")
    assert model.sent == [first]


def test_a_failed_chunk_falls_back_alone_to_its_own_transcript(model: FakeModel) -> None:
    good = sentence(38, "good")
    other = sentence(38, "other")
    bad = "Um, " + sentence(38, "bad")

    def reply(text: str) -> str:
        if text.startswith("bad"):
            raise httpx.ReadTimeout("timed out")
        return text

    model.reply = reply

    assert clean(f"Um, {good} {bad} {other}") == (f"{good} {bad} {other}", "raw_fallback")


def test_a_rejected_chunk_falls_back_alone(model: FakeModel) -> None:
    good = sentence(38, "good")
    bad = sentence(38, "bad")
    model.reply = lambda text: "banana" if text.startswith("bad") else text

    assert clean(f"{good} {bad}") == (f"{good} {bad}", "raw_fallback")


def test_each_chunk_gets_a_timeout_of_3_seconds_plus_0_012_per_word(model: FakeModel) -> None:
    clean(f"{sentence(10)} {sentence(35)} {sentence(50)}")

    assert [call["timeout"] for call in model.calls] == pytest.approx([3.12, 3.42, 3.6])
