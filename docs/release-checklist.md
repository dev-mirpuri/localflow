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
- [ ] A sentence spoken quietly, leaning back from the mic, still pastes and is saved.
- [ ] `engine.log` has a `release-to-text` line per Dictation and never any of the words you said.

## App shell (T6)

Quit any installed copy, then run `npm run dev` from `app/`. Ollama should be running.

- [ ] The tray has a LocalFlow icon with Open history and Quit, and the History window opens on launch.
- [ ] Closing the History window hides it; the tray icon stays, and Open history brings it back.
- [ ] Dictation works with no console window, and the Oval appears while dictating and hides when done.
- [ ] Press the Hotkey right after launch: the Oval shows the `loading` state until the models are ready.
- [ ] Run `npx electron .` from `app/` while the App runs: the History window comes forward and no second tray icon appears.
- [ ] End the Engine's `python.exe` in Task Manager: the Oval shows that the engine stopped, no error dialog appears, and the Engine doesn't restart.
- [ ] After a dictation, Quit from the tray: `ollama ps` no longer lists the cleanup model, and Task Manager shows no `python.exe`, `uv.exe` or `localflow-engine.exe` left.

## The Oval (T7)

Run `npm run dev` from `app/` with Ollama running, and Notepad maximized on the main screen. Today the Engine's only messages are "Starting up…", "Downloading speech model…", the transcription error and the engine-stopped error, so the message checks below use the download and the engine-stopped error.

- [ ] `npm run lint` and `npm run typecheck` pass in `app/`.
- [ ] Hold the Hotkey and speak: the Oval appears bottom centre, just above the taskbar, with 7 bars that follow your voice. Release: the same bars settle into 3 pulsing dots, then the Oval hides when the text lands.
- [ ] Double-tap: ✕ and ✓ appear beside the bars. ✓ finishes and pastes; ✕ cancels and pastes nothing. Each works on the first click, and typing still lands in Notepad afterwards.
- [ ] Double-tap, then end the Engine's `python.exe` in Task Manager: the engine-stopped error replaces the bars on one line in a wider Oval, stays about 4 s even though the Engine already went idle, then the Oval hides with no bars or buttons left. No error dialog appears.
- [ ] Press the Hotkey right after launch: "Starting up…" shows in plain text, not as an error, until the models are ready.
- [ ] Turn on Settings > Accessibility > Visual effects > Animation effects off: the bars hold still and the dots don't pulse. Turn it back on.
- [ ] The Oval's motion looks as smooth as spike S3's: no flicker or stutter in the bars, morph or dots.
- [ ] Click-through while listening and processing: clicks on the Oval reach Notepad. Only ✕ and ✓ in hands-free take clicks.
- [ ] No error dialog appears at any point, including when quitting while the Oval shows.

First run, which also gives the long-lived message for S3's test. Rename `%USERPROFILE%\.cache\huggingface\hub\models--istupakov--parakeet-tdt-0.6b-v2-onnx`, then start the App: it downloads about 2.5 GB again. Afterwards, delete the new folder and rename the old one back, or keep the new one and delete the old; rename it again to rerun.

- [ ] "Downloading speech model…" shows in plain text for the whole download, presses during it record nothing, and dictation works once it finishes.
- [ ] **S3's Notepad test with a message showing** (ADR-0003): while "Downloading speech model…" shows, click into Notepad once, then type a letter and press the Hotkey, 20 times. Each letter lands in Notepad, all 20 times, and the Oval never takes focus.
- [ ] **Click-through with a message showing:** while it shows, click on and around the Oval for about 15 s. Every click reaches Notepad (the caret moves), and nothing happens on the Oval.

## History list (T8a)

Run `npm run dev` from `app/` with Ollama running and a few Entries in `%APPDATA%\LocalFlow Dev\history.db`, including one from yesterday or earlier and one `raw_fallback` (see T4b).

- [ ] `npm run lint` and `npm run typecheck` pass in `app/`.
- [ ] The History window lists the Entries newest first under Today, Yesterday and dated labels, and each day label sticks to the top while its group scrolls.
- [ ] Each Entry shows its Cleaned text clamped to two lines, the time, the Target app, and Copy. Delete appears only on row hover or when Tab reaches the row, and nothing in the row shifts when it does.
- [ ] A long Entry has Show all; a short one doesn't. Clicking the text or Show all expands it; Show less clamps it again. Drag-selecting part of the text selects it and doesn't expand or clamp.
- [ ] Copy shows "Copied" in blue for about 1.4 s. Paste into Notepad: the text matches the Entry, with no trailing space.
- [ ] Delete removes the row at once with a quick collapse and no confirmation. Click Delete twice quickly without moving the mouse: only one Entry goes. Restart the App: the deleted Entry stays gone.
- [ ] Hover the "uncleaned" tag: its tooltip reads "Cleanup didn't finish, so this is the raw transcript."
- [ ] With the History window open, dictate a sentence into Notepad: its Entry appears at the top under Today without reopening the window.
- [ ] Narrow the window to its smallest: the time, Target app and tag wrap, and Copy and Delete stay in view.
- [ ] With Narrator on, Tab to Copy and Delete: each is read with the start of its Entry, like "Copy: Sounds good, see you at 4pm."
- [ ] Rename `history.db` while the App is closed, then start it: the window shows one line, "Hold Right Ctrl and speak", with the key in a key cap. Rename it back afterwards.
