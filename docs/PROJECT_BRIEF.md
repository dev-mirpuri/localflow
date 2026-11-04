# LocalFlow — project brief

> Working name. A free, fully local, English-only take on Wispr Flow for Windows.
> This brief is the source of truth for **scope and design**. The day-by-day plan (commands, routines, timings) is the separate "LocalFlow build roadmap". When an ADR in `docs/adr/` changes a decision here, update this file and link the ADR.
> **Simplicity is the top requirement.** If something isn't in section 2, it doesn't get built.

## 1. What it is

Press a hotkey in any app where you can type (a terminal, Claude Code, Slack, a browser, anything), speak, and clean, punctuated text appears at your cursor. Speech recognition and cleanup both run on my own PC, with no cloud, no account and no subscription. A small oval at the bottom of the screen shows when it's listening. Opening the app shows everything I've dictated, so I can copy anything I said before.

**My machine:** Windows, AMD Ryzen 5 3600, NVIDIA RTX 2060 (6 GB VRAM).
**What I know:** Python (FastAPI, pandas, pytest), TypeScript/JavaScript, React, Tailwind, HTML/CSS, SQL. No Rust. Electron is new to me but it's just JavaScript and HTML.

## 2. Core features (v1 — this is the whole product)

1. **Dictate anywhere** with one global hotkey (one key or a combination), set to hold, double-tap or both:
   - **Hold** → push-to-talk; release to finish. Pressing any other key cancels.
   - **Double-tap** → hands-free; tap again, or click ✓ on the oval, to finish. Other keys are ignored, so I can switch windows.
   - **Esc** (or ✕ on the oval) cancels the recording in progress. Once I've finished speaking, a dictation can't be stopped; Esc then goes to the app I'm typing in.
   - Recording finishes by itself after 3 minutes and is processed normally.
   - Starting a new dictation while earlier ones are processing queues them; they paste in order.
2. **Speech recognition** with NVIDIA Parakeet (English) on the GPU.
3. **Cleanup** with a small local model through Ollama: remove filler words, fix punctuation and capitals, resolve self-corrections ("at 3, no, 4pm" → "at 4pm"), format spoken lists (reliably only in short dictations; long ones stay inline in v1). It must never answer or act on what I said — it only rewrites it. If cleanup fails, paste the raw text.
4. **Paste at the cursor** of whichever text box has focus at paste time, then put my clipboard back.
5. **The oval**: appears at the bottom centre of the main screen while dictating — moving level bars while listening, ✕ and ✓ buttons in hands-free mode, dots while processing, a short message on error. It never takes focus from the app I'm typing in.
6. **History window**: every dictation, newest first, grouped by day, each with a copy button and a delete button, plus a search box and a "Show more" button. Entries are kept until I delete them; delete is immediate, with no confirmation or undo.
7. **Tray icon**: Open history, Settings, Quit. Closing the history window hides it; the app keeps running.
8. **Settings view** for the hotkey and trigger (hold, double-tap or both), and nothing else.
9. **Config file** for the microphone, cleanup model and launch at login (off by default). It also stores what the settings view saves.

### Explicitly NOT in v1 (do not build, do not design around)

Login or accounts; stats, streaks or greetings; themes (one look only); showing the raw transcript; following the cursor across monitors; first-run wizard; personal dictionary; snippets; per-app tone; command mode; audio playback; multiple languages; mobile; cloud sync; auto-update; the public web demo / live link.

## 3. Reference: how Wispr Flow does it

- A main window (the "Hub") with a searchable history grouped by date; hovering an entry shows copy.
- The "Flow Bar": a small floating pill at the bottom of the screen that shows recording and processing, with cancel and confirm buttons.
- Hold the hotkey to talk; double-tap it for hands-free; Esc cancels.
- Cleanup runs on fine-tuned Llama models on cloud GPUs. Ours runs a small model on my GPU, so it handles light cleanup well but isn't as strong at heavy rewording.

Sources: docs.wisprflow.ai ("Navigating the Wispr Flow App", "Move and Dock the Flow Bar on Desktop"); wisprflow.ai/whats-new; baseten.co/customers/wispr-flow.

## 4. Architecture

Two parts, in the two languages I know. Electron starts the Python engine and talks to it by sending JSON lines through the engine's standard input and output. There is no web server, no port and no token, so nothing else on the PC can reach the engine.

```
┌──────────────── Electron app (TypeScript + React + Tailwind) ────────────────┐
│  main process: tray, history window, oval window, starts the engine           │
│  renderer: history page, oval page (React + Tailwind)                          │
└───────────────────────────── stdin / stdout (JSON lines) ─────────────────────┘
                                        │
┌──────────────────────────── Python engine (one package) ──────────────────────┐
│ hotkey ─► record mic ─► Parakeet (GPU) ─► Ollama cleanup ─► paste at cursor   │
│                                   └──────────► SQLite history                  │
└────────────────────────────────────────────────────────────────────────────────┘
```

Choices marked **(spike)** are provisional until their spike in section 7 records an ADR.

### Python engine (Python 3.12, managed with uv)

| Part | Choice | Notes |
|---|---|---|
| Hotkey | `keyboard` library ([ADR-0002](adr/0002-s2-hotkey-and-paste.md)) | Needs key-down and key-up; ignore auto-repeat |
| Microphone | `sounddevice`, 16 kHz mono | Sends a 0–1 level about 20 times a second for the oval's bars. Opens on key-down ([ADR-0002](adr/0002-s2-hotkey-and-paste.md)). Config matches the device by name; empty means the system default; the device list goes in the log |
| Speech | Parakeet TDT 0.6B v2 via `onnx-asr` on CUDA ([ADR-0001](adr/0001-s1-speech-and-cleanup-models.md)) | Recordings over ~20 s go through VAD first; shorter ones go straight to Parakeet. Fallback: `faster-whisper` with `distil-large-v3` |
| Cleanup | `ollama` Python package with `qwen3:1.7b` ([ADR-0001](adr/0001-s1-speech-and-cleanup-models.md)) | `think=False`; `keep_alive=-1`; warm both models up at start; Quit unloads the model with `keep_alive=0` to free the VRAM |
| Paste | Save clipboard → set text → Ctrl+V → restore clipboard after 200 ms ([ADR-0002](adr/0002-s2-hotkey-and-paste.md)) | The 200 ms is unmeasured; revisit it if restores fail in daily use. Saves and restores every format that can be copied as a memory block (text, HTML, images, files) and skips the rest; keeps the dictation text out of Win+V history. Admin windows can't be pasted into (detected by comparing elevation); the oval says "Couldn't paste — copied to history" |
| Target app | Foreground window's process name at paste time (Win32 via `ctypes`) | Shown in history only |
| History | `sqlite3` (standard library) | One table, see below. The entry is saved before the paste |

**Hotkey rules (key and timings set by [ADR-0002](adr/0002-s2-hotkey-and-paste.md); two-key and three-key hotkeys are untested):**
- The hotkey is one or more of Ctrl, Shift, Alt, Win and the F-keys. A lone Alt or lone Win is rejected. An invalid hotkey falls back to the default, with an error on the oval.
- It counts as pressed when all its keys are down, in any order, and released as soon as any one comes up. A double-tap is press, release, press within 350 ms.
- Default key: Right Ctrl. Default trigger: `both`.

Trigger `both`:
- Key down → start recording at once.
- Released after ≥ 250 ms → push-to-talk done → process.
- Released before 250 ms → wait up to 350 ms for a second tap. Second tap → hands-free. No second tap → discard.

Trigger `hold`: key down → start recording. Released after ≥ 250 ms → process. Released before 250 ms → discard at once, with no wait for a second tap.

Trigger `double_tap`: recording starts on the second tap. A long press does nothing.

All triggers:
- During push-to-talk, any key not in the hotkey cancels. The engine's own Ctrl+V doesn't count.
- In hands-free, the next tap (or ✓) finishes; other keys are ignored.
- Esc (or ✕) cancels the recording in progress and is swallowed only while recording. At any other time, including processing, Esc passes through to the target app.
- Recording finishes by itself after 3 minutes of elapsed time and is processed normally.
- Under ~0.3 s or silent → discard without calling the models.

**Queue:**
- A new recording can start while earlier dictations are processing. One worker handles them in order.
- A paste waits until no hotkey keys are physically down, so Ctrl+V can't combine with held keys.
- The oval shows listening over processing. An error from a queued dictation waits until the current recording ends.

**Cleanup rules:**
- Transcript wrapped in tags; the prompt says "output only the cleaned text". The full prompt, word for word, is in [ADR-0001](adr/0001-s1-speech-and-cleanup-models.md).
- 3 words or fewer → skip the model and use the transcript unchanged.
- Pre-pass before the model: plain text matching deletes standalone "um", "uh" and "erm" in any case and "er" in lowercase only, plus a comma straight after.
- Chunks: split the joined transcript at sentence ends. A sentence under 4 words stays attached to the next one. Group into chunks of up to ~40 words without splitting a sentence, clean each with the same prompt and rule, and join them.
- On error, timeout or rejected output → raw fallback: paste that chunk's transcript. If the pre-pass leaves nothing, the same applies.
- The timeout for each chunk is ~3 s + ~0.012 s per word.
- Output is rejected unless at least 80% of its words appear in the text sent to the model, ignoring list numbers, and it's between 0.60× and 1.3× as long.
- Numbered lists are formatted reliably only in short dictations; long ones stay inline in v1.
- Known weakness: a self-corrected name can keep the wrong name, and the rejection rule can't catch it (eval clips 08 and 22).

**Pasted text:** trailing whitespace is stripped, then one trailing space is added to the paste only (not the entry or the copy button). Inner newlines stay, including in terminals, where they neither run nor submit anything ([ADR-0002](adr/0002-s2-hotkey-and-paste.md)).

**Failed transcription:** the recording is saved to `last-failed.wav` in the data folder, overwritten each time, and the oval shows an error. No entry and no retry UI.

**Startup:**
- While models load, a hotkey press shows "Still loading…" on the oval and records nothing.
- During the first-run Parakeet download, the oval shows "Downloading speech model…" until it finishes.
- Ollama or the cleanup model missing → the oval shows the error; dictation still works with raw fallback.
- GPU or Parakeet unavailable → every press shows the error.

**Protocol** (one JSON object per line; stdout carries only protocol messages — all logging goes to stderr and a log file):
- Engine → app: `{"type":"state","state":"loading|idle|listening|handsfree|processing"}`, `{"type":"level","value":0.42}`, `{"type":"result","entry":{…}}`, `{"type":"error","message":"…"}`, `{"type":"config","hotkey":["right ctrl"],"trigger":"both","launch_at_login":false}`, `{"type":"reply","id":3,"data":…}`.
- App → engine: `{"type":"request","id":3,"method":"list_history","params":{"query":"","limit":200}}`, `{"type":"request","id":4,"method":"delete_entry","params":{"id":12}}`, `{"type":"request","id":5,"method":"capture_hotkey","params":{}}`, `{"type":"request","id":6,"method":"save_settings","params":{"hotkey":["right ctrl"],"trigger":"both"}}`, `{"type":"command","name":"finish|cancel"}`.
- `config` is sent at startup and after every settings change.
- `capture_hotkey` pauses the hotkey and replies with the full set of keys held once they're released. Esc aborts. Invalid combinations reply with a message for the settings view.
- `save_settings` takes effect at once, or when the active recording ends.
- "Show more" sends `list_history` again with a higher `limit`. Search is a case-insensitive substring match on `clean_text` across all entries.

**History table:** `id, created_at, raw_text, clean_text, target_app, status (ok | raw_fallback)`. Delete removes the whole row.

**Config:** the engine is the only reader and writer of `config.json`, and creates it with defaults if missing. If the JSON is invalid, the engine uses defaults, shows an error and never overwrites the file; `save_settings` is refused with that error.

**Data folder:** `%APPDATA%\LocalFlow` (history, `config.json`, logs). When running from source (`npm run dev`), use `%APPDATA%\LocalFlow Dev`, so testing never touches real history. The app passes the folder to the engine as `--data-dir`. Quit the installed copy before `npm run dev`, or both will respond to the hotkey.

**Logs:** timings and error types only, never transcript or cleaned text. The log file is size-limited.

**Engine lifetime:** the engine exits when its stdin closes.

### Electron app (TypeScript, scaffolded with electron-vite's `react-ts` template)

- **Main process:** creates the tray, the history window and the oval window; starts the engine (`uv run` in development, the bundled exe when installed); forwards engine messages to the windows and requests back. Restarts the engine up to 3 times after a crash, then shows an error on the oval.
- **Single instance:** Electron's single-instance lock; a second launch opens the history window. Opening by hand shows the history window; a launch at login stays in the tray.
- **Preload:** exposes one small `window.localflow` object (`onEvent`, `request`, `command`, `copy`) through `contextBridge`. No Node access in the pages.
- **Oval window:** frameless, `transparent: true`, `focusable: false`, always on top at the `screen-saver` level, shown with `showInactive()`, click-through (`setIgnoreMouseEvents`) except while the ✕/✓ buttons are visible. Built exactly the way spike S3 proved.
- **History window:** an ordinary window; closing hides it. Settings is a second view inside it, not a third window.
- **Fake bridge:** when the pages run in a normal browser (no `window.localflow`), they use sample data, cover the settings view and cycle the oval's states. This is how Playwright screenshots the UI. Keep it under ~60 lines, and list both pages' dev-server URLs in the README.
- **Launch at login:** `app.setLoginItemSettings` from the value in the engine's `config` message.

**Later, for a web demo:** wrap the engine's `transcribe()` and `clean()` functions in a small FastAPI app. They don't change, so nothing built now is wasted.

## 5. UI spec

Calm, fast and clean, like Wispr Flow, Raycast or Linear. One look, no themes. Typography and spacing do the work; colour is used sparingly. The chosen direction is recorded in `PRODUCT.md` and `DESIGN.md` at the repo root (written with impeccable on day 5); those files decide colours, type, spacing and motion, and this section decides what's on each screen.

**History window**
- Search box at the top, with a gear icon that opens the settings view.
- Entries newest first, grouped under Today / Yesterday / date, with "Show more" at the end of the list.
- Each entry: the cleaned text (two lines, click to expand), time, the app it went into, a copy button (shows "Copied" briefly) and a delete button. Raw-fallback entries get a small "uncleaned" tag.
- Empty state: one line teaching the configured hotkey and trigger (e.g. "Hold Right Ctrl and speak").

**Settings view**
- The current hotkey with a "Change hotkey" button. Clicking it waits for the new keys; Esc aborts; an invalid combination shows a message here.
- The trigger: hold, double-tap or both.
- Changes save at once, with no Save button.

**The oval**
- Bottom centre of the main screen, just above the taskbar.
- Listening: level bars that move with my voice.
- Hands-free: the same, plus ✕ and ✓.
- Processing: the bars settle into pulsing dots.
- Done: disappears. Error: one short line (e.g. "Ollama isn't running"), then disappears.
- Startup: "Still loading…" if the hotkey is pressed during warm-up; "Downloading speech model…" for as long as the first-run download takes.

## 6. Targets

- Release-to-text ≤ ~1.5 s for one or two sentences (timings written to the log). Longer dictations can take longer.
- VRAM ≤ ~5 GB with both models loaded.
- Nothing I finish saying is lost: if cleanup fails, the raw text is pasted and saved; if the paste fails, the entry is still saved; if transcription fails, the recording is kept in `last-failed.wav`. (Cancelled recordings, accidental taps and silent clips are deliberately thrown away.)
- Small codebase: aim for under ~2,000 lines including tests, not counting the generated template.

## 7. Spikes (before any real code)

Throwaway prototypes in `spikes/`, half a day each, each ending in an ADR with measured numbers. Spike code is never imported by real code.

| Spike | Question | Pass bar | If it fails |
|---|---|---|---|
| S1 Models | Do Parakeet and the cleanup candidates run fast enough on this PC, and which cleans best? | Parakeet under 0.5 s per 10 s of speech; cleanup never answers or obeys the eval clips, under 0.8 s each | faster-whisper; a different cleanup model or prompt |
| S2 Hotkey and paste | Do hold and double-tap feel right, and does paste work everywhere I type? | No misfires in 50 mixed presses; paste works in Notepad, Chrome, VS Code, Slack, Windows Terminal and Claude Code | Change key or timings; typed input for apps where Ctrl+V fails |
| S3 Oval focus | Can an Electron window appear, animate and take a click without stealing focus from Notepad? | Typing keeps landing in Notepad 20 times out of 20 | Draw the oval from Python with tkinter instead |

S1 is done: the results and known failures are in [ADR-0001](adr/0001-s1-speech-and-cleanup-models.md). Eval clips 19–24 are a holdout and are never used for tuning. They're now a weaker check, because the pre-pass was added after seeing clips 19 and 20 fail.

S2 is done: the results are in [ADR-0002](adr/0002-s2-hotkey-and-paste.md). Its pass bar is met. Two-key and three-key hotkeys, image and file restore, and the restore wait from the list below were not run, and stay open there.

**S1 also:**
- Proves a PyInstaller-bundled exe transcribes on the GPU, rather than leaving that risk to T10.
- Checks VRAM use on a 3-minute clip; lower the cap if it runs out of memory.
- Measures the cleanup rate for the timeout, and tunes the output rejection numbers.
- Confirms whether Parakeet adds capitals and punctuation.
- Scores candidates with `eval/run.py` on real Parakeet transcripts: any `must_not_obey` failure rules a model out; the rest rank by normalized exact matches against `expected`, then by speed.

**S2 also:**
- Tests two-key and three-key hotkeys, not just a single key.
- Checks that Esc can be swallowed only while recording, without adding typing lag.
- Tests pasted newlines in Windows Terminal and Claude Code.
- Measures whether opening the mic on key-down clips first words.
- Tests clipboard restore with a copied image and a copied file, and measures how long to wait before restoring.

## 8. Tickets and milestones

`/to-tickets` makes the real list; this is the target. Each ticket ends with something that runs.

| # | Ticket | Milestone |
|---|---|---|
| T1 | Engine package; `transcribe <file.wav>` on the GPU with warm-up and timing, and VAD over ~20 s | M1 |
| T2 | `clean()` with Ollama, the cleanup rules (pre-pass, chunks, rejection) and raw fallback; `eval/run.py` over the eval clips | M1 |
| T3 | Hotkey state machine (hold, double-tap, Esc, combinations, trigger modes) as pure code with fake-clock tests | M1 |
| T4 | Record → transcribe → clean → paste end to end with the queue, from a console | M1 |
| T5 | History table and the JSON-lines protocol (events, requests, commands, including `config`, `capture_hotkey` and `save_settings`) | M2 |
| T6 | Electron app: tray, starts the engine, relays messages, fake bridge | M2 |
| T7 | The oval: all states, level bars, hands-free buttons | M2 |
| T8 | History window: grouped list, copy, delete, search, empty state | M3 |
| T9 | Config file, launch at login, clear error messages (Ollama down, no mic, admin window) | M3 |
| T10 | Package: engine exe (PyInstaller) inside an electron-builder installer; README setup steps | M3 |
| T11 | Settings view: change hotkey, choose trigger, applied at once | M3 |

- **M1 Works everywhere:** dictate into any app from a console window, within the 1.5 s target.
- **M2 Live:** the oval works over every app and every dictation is saved.
- **M3 v1.0:** history window, settings view, tray and installer; a fresh Windows account installs and dictates in 10 minutes.

## 9. Working with Claude Code

**Put this block at the top of CLAUDE.md, word for word:**

```markdown
## Keep it simple (most important rule)
- Two parts only: the Python engine and the Electron app, talking over stdin/stdout JSON lines.
  No servers, ports, APIs, sidecar frameworks or background services.
- Build only what the current ticket needs. No options, plugins, abstractions or future-proofing.
- Plain functions first; a class only when it holds real state.
- No new dependency without asking me.
- Tests only for logic that can break: hotkey timing, cleanup fallback, history, the protocol.
- If a change adds more than ~200 lines (not counting tests), stop and explain why first.
- Prefer deleting code to adding it.
- stdout in the engine is the protocol; log to stderr.
```

**Workflow (Matt Pocock's skills, installed with `npx skills@latest add mattpocock/skills`):**
1. `/setup-matt-pocock-skills` once: GitHub Issues, default labels, single-context docs.
2. `/grill-with-docs` on this brief, one session, to close anything still open. (No wayfinder: the scope fits one session.)
3. The `prototype` skill for the three spikes in section 7.
4. `/to-spec`, then `/to-tickets` in the same session.
5. `/implement #N` per ticket, one fresh session each, on a `t/<number>-<name>` branch off `dev`.
6. `diagnosing-bugs` when something is flaky or slow; `/handoff` when stopping mid-ticket; `/ask-matt` when unsure.

**Design tools:**
- Anthropic's `frontend-design` skill, for a deliberate look.
- impeccable (`npx impeccable install`): `init` (PRODUCT.md), `shape`, `document` (DESIGN.md), then `critique` and `polish` after each UI ticket.
- Playwright MCP (`claude mcp add playwright -- cmd /c npx @playwright/mcp@latest`): screenshots the pages through the fake bridge.
- Context7 MCP (`claude mcp add --scope user context7 -- cmd /c npx -y @upstash/context7-mcp`): current docs for Electron, electron-vite and Tailwind.

**Not used:** Tauri/Rust, FastAPI (until the web demo), wayfinder, implement-spec, obra/superpowers, shadcn MCP, Vercel guidelines, a UI-reviewer subagent, architecture-review skills. Read any third-party skill's SKILL.md before installing it.

## 10. Repo, quality and branches

```
localflow/
  engine/      Python package (uv): src/localflow_engine, tests
  app/         Electron app (electron-vite react-ts template, npm)
  docs/        PROJECT_BRIEF.md, adr/, agents/ (from Matt's setup), release-checklist.md, dogfood.md
  eval/        audio/, cases.jsonl, record.py, run.py
  spikes/      throwaway prototypes
  .githooks/   pre-commit, pre-push
  .claude/     settings.json (deny rules, format hook), hooks/
  .github/     workflows/ci.yml, rulesets/
  CLAUDE.md, GLOSSARY.md, PRODUCT.md, DESIGN.md
```

- **Python:** ruff (lint and format), pytest. Tests that need the GPU or real Windows input are marked and skipped in CI.
- **TypeScript:** the template's ESLint, Prettier and type-check. No frontend test framework in v1.
- **Git hooks** (plain scripts in `.githooks/`, enabled with `git config core.hooksPath .githooks`): pre-commit runs ruff, pytest and the app's lint and type-check; pre-push refuses any push to `main`.
- **CI:** one GitHub Actions workflow on `ubuntu-latest` for pull requests to `dev` and `main`: ruff, pytest, lint, type-check.
- **Claude Code:** deny rules block pushing to `main`, force-pushing, `gh pr merge` and changing repo settings or rulesets; a PostToolUse hook formats every file Claude saves.

**Branches:**
- `main`: only versions I've run and approved. Changes only through a promotion pull request from `dev`, merged by me with a merge commit (never squash). Releases are tagged here.
- `dev`: the default branch. Every finished ticket, squash-merged by me.
- `t/<number>-<name>`: one ticket, built by Claude with `/implement`.
- Optional GitHub ruleset on `main` (free on a public repo): require a pull request and green CI.
- Before promoting, I run `dev` and work through `docs/release-checklist.md`. Any ticket that adds something visible adds its check there.

## 11. Packaging and release

- The engine is bundled as a folder with one exe using PyInstaller and shipped inside the Electron installer (electron-builder `extraResources`).
- The installer is the NSIS one electron-builder makes by default. Unsigned, so Windows SmartScreen will warn.
- Models aren't bundled. The README says: install Ollama, run `ollama pull <model>`; Parakeet downloads on first run.
- On start, the engine checks the GPU, Ollama and the models, and sends a clear error to the oval if anything is missing (see Startup in section 4).
- Supported machines: NVIDIA GPUs with at least 6 GB VRAM. Anything else gets a clear error; there is no CPU mode.
- Releases are built on my PC from `main` and uploaded with `gh release create`. No release pipeline.
