import json
import sys

from localflow_engine import config, history, protocol


def serve(
    capfd, data_dir, *lines: dict | str, commands: list | None = None, settings=config.DEFAULTS
) -> list[dict]:
    """Runs the protocol loop over these lines, then reads stdout back as JSON lines."""
    sent = [line if isinstance(line, str) else json.dumps(line) + "\n" for line in lines]
    command = (commands if commands is not None else []).append
    protocol.serve(iter(sent), data_dir, settings, command)
    return [json.loads(line) for line in capfd.readouterr().out.splitlines()]


def request(id: int, method: str, /, **params) -> dict:
    return {"type": "request", "id": id, "method": method, "params": params}


def save(data_dir, *clean_texts: str) -> list[int]:
    db = history.open_history(data_dir / "history.db")
    return [history.save(db, text.lower(), text, "notepad.exe", "ok")["id"] for text in clean_texts]


def test_config_is_sent_at_startup_with_the_defaults(capfd, tmp_path):
    assert serve(capfd, tmp_path) == [
        {"type": "config", "hotkey": "right ctrl", "launch_at_login": False}
    ]


def test_config_reports_the_configured_hotkey_and_launch_at_login(capfd, tmp_path):
    settings = {**config.DEFAULTS, "hotkey": "left shift", "launch_at_login": True}

    assert serve(capfd, tmp_path, settings=settings) == [
        {"type": "config", "hotkey": "left shift", "launch_at_login": True}
    ]


def test_list_history_replies_newest_first_up_to_the_limit_with_the_request_id(capfd, tmp_path):
    save(tmp_path, "One.", "Two.", "Three.")

    *_, reply = serve(capfd, tmp_path, request(7, "list_history", query="", limit=2))

    assert reply["type"] == "reply"
    assert reply["id"] == 7
    assert [entry["clean_text"] for entry in reply["data"]] == ["Three.", "Two."]
    assert set(reply["data"][0]) == {
        *("id", "created_at", "raw_text", "clean_text", "target_app", "status")
    }


def test_search_matches_clean_text_in_any_case_across_all_entries(capfd, tmp_path):
    save(tmp_path, "Call the DENTIST at noon.", *[f"Note {n}." for n in range(250)])

    *_, reply = serve(capfd, tmp_path, request(1, "list_history", query="dentist", limit=200))

    assert [entry["clean_text"] for entry in reply["data"]] == ["Call the DENTIST at noon."]


def test_search_treats_percent_and_underscore_as_plain_text(capfd, tmp_path):
    save(tmp_path, "Up 50% today.", "Up 50 today.", "snake_case", "snakeXcase")

    *_, percent = serve(capfd, tmp_path, request(1, "list_history", query="50%", limit=200))
    *_, underscore = serve(capfd, tmp_path, request(2, "list_history", query="e_c", limit=200))

    assert [entry["clean_text"] for entry in percent["data"]] == ["Up 50% today."]
    assert [entry["clean_text"] for entry in underscore["data"]] == ["snake_case"]


def test_delete_entry_removes_the_whole_row_and_replies(capfd, tmp_path):
    first, second = save(tmp_path, "One.", "Two.")

    *_, deleted, listed = serve(
        capfd,
        tmp_path,
        request(4, "delete_entry", id=first),
        request(5, "list_history", query="", limit=200),
    )

    assert deleted == {"type": "reply", "id": 4, "data": None}
    assert [entry["id"] for entry in listed["data"]] == [second]


def test_finish_and_cancel_commands_are_passed_on_in_order(capfd, tmp_path):
    commands = []

    serve(
        capfd,
        tmp_path,
        {"type": "command", "name": "finish"},
        {"type": "command", "name": "cancel"},
        commands=commands,
    )

    assert commands == ["finish", "cancel"]


def test_a_bad_line_is_logged_to_stderr_and_later_requests_still_get_replies(capfd, tmp_path):
    save(tmp_path, "One.")

    sent = serve(
        capfd,
        tmp_path,
        "not json\n",
        request(1, "no_such_method"),
        request(2, "list_history"),
        request(3, "list_history", query="", limit=200),
    )

    assert [message["type"] for message in sent] == ["config", "reply"]
    assert sent[-1]["id"] == 3


def test_messages_reach_the_real_stdout_while_sys_stdout_points_at_stderr(
    capfd, tmp_path, monkeypatch
):
    """The Engine points sys.stdout at stderr, so a stray print can't corrupt the protocol."""
    monkeypatch.setattr(sys, "stdout", sys.stderr)

    assert serve(capfd, tmp_path)[0]["type"] == "config"
