# LocalFlow — project brief

> Working name. A free, fully local, English-only take on Wispr Flow for Windows.
> This brief is the source of truth for **scope and design**. The day-by-day plan (commands, routines, timings) is the separate "LocalFlow build roadmap". When an ADR in `docs/adr/` changes a decision here, update this file and link the ADR.
> **Simplicity is the top requirement.** If something isn't in section 2, it doesn't get built.

## 1. What it is

Press a hotkey in any app where you can type (a terminal, Claude Code, Slack, a browser, anything), speak, and clean, punctuated text appears at your cursor. Speech recognition and cleanup both run on my own PC, with no cloud, no account and no subscription. A small oval at the bottom of the screen shows when it's listening. Opening the app shows everything I've dictated, so I can copy anything I said before.

**My machine:** Windows, AMD Ryzen 5 3600, NVIDIA RTX 2060 (6 GB VRAM).
**What I know:** Python (FastAPI, pandas, pytest), TypeScript/JavaScript, React, Tailwind, HTML/CSS, SQL. No Rust. Electron is new to me but it's just JavaScript and HTML.

## 2. Core features (v1 — this is the whole product)

1. **Dictate anywhere** with one global hotkey:
   - **Hold** → push-to-talk; release to finish.
   - **Double-tap** → hands-free; tap again, or click ✓ on the oval, to finish.
   - **Esc** (or ✕ on the oval) cancels and discards that recording.
2. **Speech recognition** with NVIDIA Parakeet (English) on the GPU.
3. **Cleanup** with a small local model through Ollama: remove filler words, fix punctuation and capitals, resolve self-corrections ("at 3, no, 4pm" → "at 4pm"), format spoken lists. It must never answer or act on what I said — it only rewrites it. If cleanup fails, paste the raw text.
4. **Paste at the cursor** of whatever app was focused, then put my clipboard back.
5. **The oval**: appears at the bottom centre of the main screen while dictating — moving level bars while listening, ✕ and ✓ buttons in hands-free mode, dots while processing, a short message on error. It never takes focus from the app I'm typing in.
6. **History window**: every dictation, newest first, grouped by day, each with a copy button and a delete button, plus a search box.
7. **Tray icon**: Open history, Quit. Closing the history window hides it; the app keeps running.
8. **Config file** for the hotkey, microphone, cleanup model and launch at login. No settings screen.

### Explicitly NOT in v1 (do not build, do not design around)

Login or accounts; settings screen; stats, streaks or greetings; themes (one look only); showing the raw transcript; following the cursor across monitors; first-run wizard; personal dictionary; snippets; per-app tone; command mode; audio playback; multiple languages; mobile; cloud sync; auto-update; the public web demo / live link.

## 3. Reference: how Wispr Flow does it

- A main window (the "Hub") with a searchable history grouped by date; hovering an entry shows copy.
- The "Flow Bar": a small floating pill at the bottom of the screen that shows recording and processing, with cancel and confirm buttons.
- Hold the hotkey to talk; double-tap it for hands-free; Esc cancels.
- Cleanup runs on fine-tuned Llama models on cloud GPUs. Ours runs a 3–4B model on my GPU, so it handles light cleanup well but isn't as strong at heavy rewording.

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
| Hotkey | `keyboard` library **(spike)** | Needs key-down and key-up; ignore auto-repeat |
| Microphone | `sounddevice`, 16 kHz mono | Sends a 0–1 level about 20 times a second for the oval's bars |
| Speech | Parakeet TDT 0.6B v2 via `onnx-asr` on CUDA **(spike)** | Fallback: `faster-whisper` with `distil-large-v3` |
| Cleanup | `ollama` Python package; candidates `qwen3:4b`, `qwen3:1.7b`, `llama3.2:3b` **(spike)** | `think=False` for Qwen3; `keep_alive=-1`; warm both models up at start |
| Paste | Save clipboard → set text → Ctrl+V → restore clipboard **(spike)** | Admin windows can't be pasted into; show a short error |
| App name | Foreground window's process name (Win32 via `ctypes`) | Shown in history only |
| History | `sqlite3` (standard library) | One table, see below |

**Hotkey rules (defaults; spike S2 sets the final key and timings):**
- Key down → start recording at once.
- Released after ≥ 250 ms → push-to-talk done → process.
- Released before 250 ms → wait up to 350 ms for a second tap. Second tap → hands-free. No second tap → discard.
- In hands-free, the next tap (or ✓) finishes. Esc (or ✕) cancels in any state.
- Under ~0.3 s or silent → discard without calling the models.
- Default key: Right Ctrl or Ctrl+Win, whichever misfires less in the spike.

**Cleanup rules:**
- Transcript wrapped in tags; the prompt says "output only the cleaned text".
- On error, a ~3 s timeout, or output wildly different in length from the input → paste the raw transcript.
- 3 words or fewer → skip the model; just capitalise and punctuate.

**Protocol** (one JSON object per line; stdout carries only protocol messages — all logging goes to stderr and a log file):
- Engine → app: `{"type":"state","state":"idle|listening|handsfree|processing|done|error|cancelled"}`, `{"type":"level","value":0.42}`, `{"type":"result","entry":{…}}`, `{"type":"error","message":"…"}`, `{"type":"reply","id":3,"data":…}`.
- App → engine: `{"type":"request","id":3,"method":"list_history","params":{"query":"","limit":200}}`, `{"type":"request","id":4,"method":"delete_entry","params":{"id":12}}`, `{"type":"command","name":"finish|cancel"}`.

**History table:** `id, created_at, raw_text, clean_text, app_name, status (ok | raw_fallback)`.

**Data folder:** `%APPDATA%\LocalFlow` (history, `config.json`, logs). When running from source (`npm run dev`), use `%APPDATA%\LocalFlow Dev`, so testing never touches real history.

### Electron app (TypeScript, scaffolded with electron-vite's `react-ts` template)

- **Main process:** creates the tray, the history window and the oval window; starts the engine (`uv run` in development, the bundled exe when installed); forwards engine messages to the windows and requests back.
- **Preload:** exposes one small `window.localflow` object (`onEvent`, `request`, `command`, `copy`) through `contextBridge`. No Node access in the pages.
- **Oval window:** frameless, `transparent: true`, `focusable: false`, always on top at the `screen-saver` level, shown with `showInactive()`, click-through (`setIgnoreMouseEvents`) except while the ✕/✓ buttons are visible. Built exactly the way spike S3 proved.
- **History window:** an ordinary window; closing hides it.
- **Fake bridge:** when the pages run in a normal browser (no `window.localflow`), they use sample data and cycle the oval's states. This is how Playwright screenshots the UI. Keep it under ~60 lines, and list both pages' dev-server URLs in the README.
- **Launch at login:** `app.setLoginItemSettings` from the config value.

**Later, for a web demo:** wrap the engine's `transcribe()` and `clean()` functions in a small FastAPI app. They don't change, so nothing built now is wasted.

## 5. UI spec

Calm, fast and clean, like Wispr Flow, Raycast or Linear. One look, no themes. Typography and spacing do the work; colour is used sparingly. The chosen direction is recorded in `PRODUCT.md` and `DESIGN.md` at the repo root (written with impeccable on day 5); those files decide colours, type, spacing and motion, and this section decides what's on each screen.

**History window**
- Search box at the top.
- Entries newest first, grouped under Today / Yesterday / date.
- Each entry: the cleaned text (two lines, click to expand), time, the app it went into, a copy button (shows "Copied" briefly) and a delete button. Raw-fallback entries get a small "uncleaned" tag.
- Empty state: one line teaching the hotkey ("Hold Right Ctrl and speak").

**The oval**
- Bottom centre of the main screen, just above the taskbar.
- Listening: level bars that move with my voice.
- Hands-free: the same, plus ✕ and ✓.
- Processing: the bars settle into pulsing dots.
- Done: disappears. Error: one short line (e.g. "Ollama isn't running"), then disappears.

## 6. Targets

- Release-to-text ≤ ~1.5 s for one or two sentences (timings written to the log).
- VRAM ≤ ~5 GB with both models loaded.
- Nothing I finish saying is lost: if cleanup fails, the raw text is pasted and saved. (Esc, accidental taps and silent clips are deliberately discarded.)
- Small codebase: aim for under ~2,000 lines including tests, not counting the generated template.

## 7. Spikes (before any real code)

Throwaway prototypes in `spikes/`, half a day each, each ending in an ADR with measured numbers. Spike code is never imported by real code.

| Spike | Question | Pass bar | If it fails |
|---|---|---|---|
| S1 Models | Do Parakeet and the cleanup candidates run fast enough on this PC, and which cleans best? | Parakeet under 0.5 s per 10 s of speech; cleanup never answers or obeys the eval clips, under 0.8 s each | faster-whisper; a different cleanup model or prompt |
| S2 Hotkey and paste | Do hold and double-tap feel right, and does paste work everywhere I type? | No misfires in 50 mixed presses; paste works in Notepad, Chrome, VS Code, Slack, Windows Terminal and Claude Code | Change key or timings; typed input for apps where Ctrl+V fails |
| S3 Oval focus | Can an Electron window appear, animate and take a click without stealing focus from Notepad? | Typing keeps landing in Notepad 20 times out of 20 | Draw the oval from Python with tkinter instead |

## 8. Tickets and milestones

`/to-tickets` makes the real list; this is the target. Each ticket ends with something that runs.

| # | Ticket | Milestone |
|---|---|---|
| T1 | Engine package; `transcribe <file.wav>` on the GPU with warm-up and timing | M1 |
| T2 | `clean()` with Ollama, the cleanup rules and raw fallback; `eval/run.py` over the eval clips | M1 |
| T3 | Hotkey state machine (hold, double-tap, Esc) as pure code with fake-clock tests | M1 |
| T4 | Record → transcribe → clean → paste end to end, from a console | M1 |
| T5 | History table and the JSON-lines protocol (events, requests, commands) | M2 |
| T6 | Electron app: tray, starts the engine, relays messages, fake bridge | M2 |
| T7 | The oval: all states, level bars, hands-free buttons | M2 |
| T8 | History window: grouped list, copy, delete, search, empty state | M3 |
| T9 | Config file, launch at login, clear error messages (Ollama down, no mic, admin window) | M3 |
| T10 | Package: engine exe (PyInstaller) inside an electron-builder installer; README setup steps | M3 |

- **M1 Works everywhere:** dictate into any app from a console window, within the 1.5 s target.
- **M2 Live:** the oval works over every app and every dictation is saved.
- **M3 v1.0:** history window, tray and installer; a fresh Windows account installs and dictates in 10 minutes.

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
  CLAUDE.md, PRODUCT.md, DESIGN.md
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
- On start, the engine checks the GPU, Ollama and the models, and sends a clear error to the oval if anything is missing.
- Releases are built on my PC from `main` and uploaded with `gh release create`. No release pipeline.
