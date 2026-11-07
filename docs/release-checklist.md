# Release checklist

Work through this on `dev` before promoting to `main`. Each ticket that adds something visible adds its checks here.

## Dictate from a console (T4a)

Run `uv run localflow-engine dictate --data-dir "$env:APPDATA\LocalFlow Dev"` from `engine/`, wait for "ready", then in each of Notepad, Chrome, VS Code, Slack, Windows Terminal and Claude Code:

- [ ] Hold Right Ctrl, say a sentence, release: the Cleaned text lands at the cursor with one trailing space, within about 1.5 s of release for one or two sentences.
- [ ] Double-tap Right Ctrl, speak, tap again: the text lands once the key is up.
- [ ] A spoken numbered list keeps its line breaks, and nothing runs or submits in the terminals.
- [ ] Copy some text first: after the paste, Ctrl+V gives that text again.
- [ ] Hold Right Ctrl and press another key: nothing is pasted, and the other key still types.
- [ ] Double-tap, then press Esc: nothing is pasted and the app doesn't see the Esc. Esc while idle still reaches the app.
- [ ] One quick tap: nothing is pasted.
- [ ] The console's level bar moves with your voice while recording.
- [ ] Hands-free left running finishes by itself after 3 minutes and pastes.

## Nothing gets lost (T4b)

Run the Engine as for T4a. The data folder is `%APPDATA%\LocalFlow Dev`; to see its rows, from `engine/`:

```powershell
uv run python -c "import os, sqlite3; [print(r) for r in sqlite3.connect(os.path.expandvars(r'%APPDATA%\LocalFlow Dev\history.db')).execute('SELECT * FROM entries')]"
```

- [ ] After a first Dictation, the data folder holds `history.db` and `engine.log`.
- [ ] Each pasted Dictation adds one row to `entries` in `history.db`, with the Transcript, the Cleaned text, the Target app's process name (like `notepad.exe`) and `ok`.
- [ ] Stop Ollama (`ollama stop qwen3:1.7b` and quit the Ollama app), then dictate a long sentence: the raw text is pasted and its row has `raw_fallback`.
- [ ] Dictate into an app running as administrator: nothing is pasted, but the row is in `history.db`.
- [ ] A quick tap, a held key with nothing said, and a Recording of only "um": nothing is pasted and no row is added.
- [ ] `engine.log` has a `release-to-text` line per Dictation and never any of the words you said.
