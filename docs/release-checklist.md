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
- [ ] Each Entry shows its Cleaned text clamped to two lines, the time, the Target app, and Copy. Delete appears only on row hover or when keyboard focus reaches the row, and nothing in the row shifts when it does.
- [ ] A long Entry has Show all; a short one doesn't. Clicking the text or Show all expands it; Show less clamps it again. Drag-selecting part of the text selects it and doesn't expand or clamp.
- [ ] Copy shows "Copied" in blue for about 1.4 s. Paste into Notepad: the text matches the Entry, with no trailing space.
- [ ] Delete removes the row at once with a quick collapse and no confirmation. Click Delete twice quickly without moving the mouse: only one Entry goes. Restart the App: the deleted Entry stays gone.
- [ ] Hover the "uncleaned" tag: its tooltip reads "Cleanup didn't finish, so this is the raw transcript."
- [ ] With the History window open, dictate a sentence into Notepad: its Entry appears at the top under Today without reopening the window.
- [ ] Narrow the window to its smallest: the time, Target app and tag wrap, and Copy and Delete stay in view.
- [ ] With Narrator on, Tab to Copy, then use Narrator's scan mode to reach Delete: each is read with the start of its Entry, like "Copy: Sounds good, see you at 4pm."
- [ ] Rename `history.db` while the App is closed, then start it: the window shows one line, "Hold Right Ctrl and speak", with the key in a key cap. Rename it back afterwards.

## History search and keyboard (T8b)

Run `npm run dev` from `app/` with Ollama running and Entries as for T8a, including one long Entry whose last few words appear nowhere near its start, and more than 200 Entries in all (dictate or insert rows; see T4b).

- [ ] `npm run lint` and `npm run typecheck` pass in `app/`.
- [ ] The search box sits at the top with "Search history" and has focus when the window opens. Close the window, open it again from the tray: search has focus again. Minimize and restore: the same.
- [ ] Type part of a word in mixed case: only Entries containing it show, with every match in blue.
- [ ] Search for words at the end of the long Entry: its row starts with "…" a few words before the match, and the match is visible without Show all. Show all shows the whole text with the match still blue.
- [ ] Search for a word only in an Entry older than the newest 200: it shows.
- [ ] Search for something you never said: one line reads "Nothing matches" and the query, with no picture.
- [ ] Type quickly, then stop: the list matches the final query, not an earlier one.
- [ ] With a query typed, dictate a sentence that matches it: it appears at the top. Dictate one that doesn't: it doesn't appear, and it shows once the search is cleared.
- [ ] Tab from search lands on one Entry's Copy, and its row fills. Up and Down move between Entries across day labels, and the row stays clear of the sticky label. Left and Right do nothing, and Show all and Delete are never reached by Tab or arrows. Tab again leaves the list; Shift+Tab comes back to the same Entry.
- [ ] Type a query, press Down, then Enter: the first matching Entry shows "Copied" without a Tab. Down with no matches does nothing.
- [ ] Enter on Copy shows "Copied" in blue and Narrator says "Copied"; paste in Notepad gives the Entry's text.
- [ ] Pressing the Delete key on a focused Entry does nothing.

## Config and clear errors (T9)

Quit any installed copy, then run `npm run dev` from `app/` with Ollama running. The config file is `%APPDATA%\LocalFlow Dev\config.json`; keep a copy of yours and put it back afterwards. Restart the App after each edit. Each error below shows on the Oval in plain words on one line, is fully readable (no "…" at the end), then hides after about 4 s. If two show at once, they appear one after the other.

- [ ] `npm run lint` and `npm run typecheck` pass in `app/`, and `uv run pytest` passes in `engine/`.
- [ ] Delete `config.json`, then start the App: it's created with `"hotkey": "right ctrl"`, `"microphone": ""`, `"cleanup_model": "qwen3:1.7b"` and `"launch_at_login": false`. Edit it, restart: your edits are still there.
- [ ] Set `"hotkey": "F8"`: F8 dictates and Right Ctrl doesn't, and the empty History state reads "Hold F8 and speak". Repeat with `"left shift"`.
- [ ] Set `"hotkey": "right alt"`, then `"win"`: "config.json: "hotkey" isn't valid, so it uses Right Ctrl. Set a Ctrl, Shift or F-key." shows at startup, and Right Ctrl dictates. Set `"launch_at_login": "yes"`: a message naming `"launch_at_login"` shows, and only that value goes back to its default.
- [ ] Break the JSON (delete a closing brace): "config.json isn't valid JSON, so it uses the defaults. Fix it and restart." shows, Right Ctrl dictates, and the file is unchanged.
- [ ] `engine.log` lists the input devices. Set `"microphone"` to part of one that isn't the default: dictation records from it. Set it to `"nothing like this"`: "Microphone not found. Copy a name from engine.log into config.json." shows, and dictation uses the default mic.
- [ ] Disable every microphone in Sound settings: at startup and on each press, "No microphone found. Plug one in, or fix its name in config.json." shows, and the next press after re-enabling one records.
- [ ] Set `"cleanup_model": "qwen3:0.6b-missing"`: "The cleanup model is missing. Run "ollama pull qwen3:0.6b-missing" and try again." shows at startup and after a dictation longer than three words, and the raw text is still pasted and saved as `raw_fallback`.
- [ ] Quit Ollama (tray icon > Quit), then start the App: "Ollama isn't running. Start Ollama and try again." shows at startup. Dictate a long sentence: the same message shows, and the raw text is pasted and saved as `raw_fallback`. Start Ollama again: the next dictation is cleaned with no error.
- [ ] Make a dictation fail to transcribe (for example, fill the VRAM by running a large model with `ollama run` before dictating a long sentence): "Couldn't transcribe that, so it's kept in last-failed.wav. Try again." shows and `last-failed.wav` is in the data folder.
- [ ] Rename `nvidia-smi.exe` in `C:\Windows\System32` (needs admin; rename it back after): "LocalFlow needs an NVIDIA GPU with 6 GB and a working driver. Update the driver and restart." shows at startup and on every press, nothing records, and History still opens and searches.
- [ ] In PowerShell, `$env:CUDA_VISIBLE_DEVICES = "-1"; npm run dev` (then close that window): "The GPU isn't available. Update the NVIDIA driver and restart LocalFlow." shows at startup and on every press, and nothing records.
- [ ] Rename the Parakeet folder (see T7) and start the App offline: after "Downloading speech model…", "The speech model didn't load. Check your internet and restart LocalFlow." shows, and again on every press instead of "Starting up…".
- [ ] Set `"launch_at_login": true`: the `npm run dev` console logs "not packaged, so no login item; would set" with `openAtLogin: true` and `--login`, and no LocalFlow entry appears in Task Manager > Startup apps. The real login item and the tray-only start are checked with the installer in T10.

## Installer (T10)

On `main`, run `npm --prefix app run build:win` from the repo root. Then, on a Windows account that has never run LocalFlow (Settings > Accounts > Other users), with Ollama installed and `qwen3:1.7b` pulled. Time it from opening the installer.

- [ ] `uv run pytest -m gpu` passes in `engine/`, including `test_packaged_engine_transcribes_on_the_gpu`.
- [ ] `app\dist\LocalFlow-<version>-setup.exe` is under 2 GB.
- [ ] Running it shows SmartScreen's "Windows protected your PC"; More info, then Run anyway installs it with no further prompts, to `%LOCALAPPDATA%\Programs\localflow`, with a LocalFlow shortcut on the desktop and in the Start menu.
- [ ] LocalFlow starts after installing, with its tray icon. "Downloading speech model…" shows while Parakeet downloads, then dictation works.
- [ ] **Install to first dictation takes 10 minutes or less**, following only the README.
- [ ] Task Manager shows `localflow-engine.exe` under LocalFlow, and no `uv.exe` or `python.exe`.
- [ ] `%APPDATA%\LocalFlow` holds `config.json`, `engine.log`, `history.db` and an `electron` folder, and nothing else.
- [ ] With both models loaded after a dictation, `nvidia-smi` shows the GPU's memory in use at or under about 5 GB more than before LocalFlow started.
- [ ] Rerun the T4a, T7, T8a, T8b and T9 checks on the installed app, with `%APPDATA%\LocalFlow` as the data folder.
- [ ] Set `"launch_at_login": true` and restart LocalFlow: Task Manager > Startup apps lists LocalFlow. Sign out and in: LocalFlow starts in the tray with no History window, and dictation works. Set it back to `false` and restart: the Startup apps entry goes.
- [ ] Quit from the tray: no `localflow-engine.exe` is left, and `ollama ps` no longer lists the cleanup model.
- [ ] With the installed copy still running, `npm run dev` from `app/` would double the Hotkey, so quit it first, as the README says.
- [ ] Uninstall from Settings > Apps: `%LOCALAPPDATA%\Programs\localflow` is gone; `%APPDATA%\LocalFlow` stays.
