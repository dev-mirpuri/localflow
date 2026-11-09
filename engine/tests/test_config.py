import json

import pytest

from localflow_engine import config

DEFAULTS = {
    "hotkey": "right ctrl",
    "microphone": "",
    "cleanup_model": "qwen3:1.7b",
    "launch_at_login": False,
}


def write(path, text: str):
    path.write_text(text, encoding="utf-8")
    return path


def test_a_missing_file_is_created_with_the_defaults(tmp_path):
    path = tmp_path / "config.json"

    assert config.load(path) == (DEFAULTS, [])
    assert json.loads(path.read_text(encoding="utf-8")) == DEFAULTS


@pytest.mark.parametrize(
    "text",
    [
        '{"hotkey": "f8", "launch_at_login": true}',
        "{not json",
        '{"hotkey": "alt"}',
        "[]",
        "",
    ],
)
def test_an_existing_file_is_never_overwritten(tmp_path, text):
    path = write(tmp_path / "config.json", text)

    config.load(path)

    assert path.read_text(encoding="utf-8") == text


def test_missing_keys_take_their_defaults_without_an_error(tmp_path):
    path = write(tmp_path / "config.json", '{"microphone": "USB Mic", "launch_at_login": true}')

    assert config.load(path) == (
        {**DEFAULTS, "microphone": "USB Mic", "launch_at_login": True},
        [],
    )


@pytest.mark.parametrize("text", ["{not json", "[]", '"right ctrl"', ""])
def test_invalid_json_uses_the_defaults_and_names_the_fix(tmp_path, text):
    path = write(tmp_path / "config.json", text)

    assert config.load(path) == (DEFAULTS, [config.INVALID])


@pytest.mark.parametrize(
    ("written", "hotkey"),
    [
        ("right ctrl", "right ctrl"),
        ("Left Ctrl", "left ctrl"),
        ("RIGHT SHIFT", "right shift"),
        ("left shift", "left shift"),
        ("F1", "f1"),
        ("f24", "f24"),
    ],
)
def test_a_ctrl_shift_or_f_key_is_accepted_in_any_case(tmp_path, written, hotkey):
    path = write(tmp_path / "config.json", json.dumps({"hotkey": written}))

    assert config.load(path) == ({**DEFAULTS, "hotkey": hotkey}, [])


@pytest.mark.parametrize(
    "hotkey",
    [
        "alt",
        "right alt",
        "left windows",
        "win",
        "a",
        "space",
        "f0",
        "f25",
        "ctrl+shift",
        "",
        5,
        [],
        {},
    ],
)
def test_alt_win_or_any_other_key_falls_back_to_right_ctrl_with_an_error(tmp_path, hotkey):
    path = write(tmp_path / "config.json", json.dumps({"hotkey": hotkey, "microphone": "USB"}))

    assert config.load(path) == ({**DEFAULTS, "microphone": "USB"}, [config.invalid("hotkey")])


@pytest.mark.parametrize(
    ("key", "value"),
    [("microphone", None), ("cleanup_model", ""), ("cleanup_model", 3), ("launch_at_login", "yes")],
)
def test_a_value_of_the_wrong_type_takes_its_default_with_an_error(tmp_path, key, value):
    path = write(tmp_path / "config.json", json.dumps({key: value}))

    assert config.load(path) == (DEFAULTS, [config.invalid(key)])


def test_each_wrong_value_is_named_with_the_default_it_uses_instead(tmp_path):
    path = write(tmp_path / "config.json", '{"hotkey": "alt", "launch_at_login": 1}')

    assert config.load(path)[1] == [
        """config.json: "hotkey" isn't valid, so it uses Right Ctrl. Set a Ctrl, Shift or F-key.""",
        """config.json: "launch_at_login" isn't valid, so it uses false. Fix it and restart.""",
    ]


def test_the_hook_names_left_keys_without_left():
    assert config.hook_name("left ctrl") == "ctrl"
    assert config.hook_name("left shift") == "shift"
    assert config.hook_name("right ctrl") == "right ctrl"
    assert config.hook_name("f8") == "f8"
