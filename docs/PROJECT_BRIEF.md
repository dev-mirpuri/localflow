# LocalFlow — project brief

> Working name. A free, fully local, English-only take on Wispr Flow for Windows.
> This brief is the source of truth for **scope and design**. The day-by-day plan (commands, routines, timings) is the separate "LocalFlow build roadmap". When an ADR in `docs/adr/` changes a decision here, update this file and link the ADR.

## 1. What it is

Press a hotkey in any app where you can type, speak, and clean, punctuated text appears at your cursor. Speech recognition and cleanup both run on my own PC, with no cloud and no subscription. Opening the app shows a polished window with the history of everything I've dictated.

**My machine:** Windows, AMD Ryzen 5 3600, NVIDIA RTX 2060 (6 GB VRAM).

## 2. Core features (v1 — this is the whole product for now)

1. **Dictate anywhere.** Global hotkey works in every app with a text field.
   - **Hold** the hotkey → push-to-talk; release to finish.
   - **Double-tap** the hotkey → hands-free mode; tap again (or click ✓ on the pill) to finish.
   - **Esc** cancels and discards that recording.
2. **Local speech recognition.** NVIDIA Parakeet (English) on the GPU.
3. **Local cleanup.** A small local LLM removes filler words, fixes punctuation and capitalisation, resolves self-corrections ("at 3, no, 4pm" → "at 4pm"), and formats spoken lists. It must never answer or act on what I said — it only rewrites it.
4. **Text lands at the cursor** of whatever app was focused.
5. **Floating pill overlay** appears while dictating: live waveform while listening, a processing state, a brief success tick, a clear error state. It never steals focus.
6. **The app (Hub window)** with a home screen showing my dictation history, a few headline stats and settings.
7. **Tray icon** with Open / Pause / Quit. Launch at login.
8. **Light, dark and system themes.**

### Explicitly NOT in v1 (later ideas — do not build, do not design around them yet)

Personal dictionary, snippets, per-app styles/tones, scratchpad/notes, command mode ("make this more formal"), audio playback of past dictations, insights page (heatmap, leaderboard, "your voice"), multiple languages, mobile, meeting notes, cloud sync, the public web demo / live link.

The one exception: keep the speech + cleanup engine behind a local HTTP API (section 4) so a web demo can reuse it later without a rewrite.

## 3. How Wispr Flow does the UI (reference, not a spec to copy)

From Wispr's own help docs:

- **Hub window** with a left sidebar: Home (default), Dictionary and Snippets, with Settings and Help pinned at the bottom.
- **Home** greets you by first name, shows usage stats (word count, your shortcut), and a **transcript history grouped by date and searchable**. Hovering an entry reveals copy and flag actions.
- **Flow Bar**: a small floating bubble showing dictation status with resting, recording and processing states. It follows the display your cursor is on, stays clear of the taskbar, and has cancel and confirm buttons. Right-click when resting → "Hide for 1 hour".
- **Hotkeys**: hold the push-to-talk key; double-tap it to toggle hands-free; Esc cancels.
- **Settings**: General (shortcuts, microphone, languages), System (launch at login, Flow Bar visibility, notifications), Account, Data & Privacy.
- **Themes**: Light, Dark, or System.
- **Insights** (later for us): words per minute, total words, fixes made, top apps, daily streak heatmap.

Sources: docs.wisprflow.ai — "Navigating the Wispr Flow App", "Move and Dock the Flow Bar on Desktop", "Your Usage tab"; wisprflow.ai/whats-new.

## 4. Architecture

Two processes. The Python **engine** does all the real work; the **app shell** is purely the UI.

```
┌──────────────────────────────── Tauri 2 app shell ─────────────────────────────┐
│  Hub window (React + TS + Tailwind + shadcn/ui)   Overlay pill window   Tray     │
│            │  REST (history, settings, stats)          │ WebSocket (live state)  │
└────────────┼───────────────────────────────────────────┼──────────────────────┘
             ▼                                           ▼
┌──────────────────────── Python engine (sidecar, 127.0.0.1 only) ───────────────┐
│ Global hotkey ─► Mic capture ─► Parakeet (GPU) ─► Ollama cleanup ─► Paste       │
│      (hold / double-tap)          raw text           clean text      at cursor  │
│                                   └─────────────► SQLite history ◄────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────┘
```

**Why this split:** Python has the best local ML tooling and solid Windows hotkey/paste libraries; web tech gives the best-looking UI; and the engine's API is exactly what a future web demo needs.

Choices marked **(spike)** are provisional until their spike in section 7 records an ADR.

### Engine (Python 3.12, managed with uv)

| Concern | Choice | Notes |
|---|---|---|
| API | FastAPI + uvicorn, bound to `127.0.0.1` on a free port | A random token, passed by the app on every call, so other programs on the PC can't read history. REST for history/settings/stats, one WebSocket for live events |
| Hotkey | `keyboard` (or `pynput`) global hook **(spike)** | Needs key-down *and* key-up for hold vs double-tap; ignore key auto-repeat |
| Audio | `sounddevice`, 16 kHz mono float32 | Stream RMS level to the overlay ~20×/sec for the waveform |
| Speech | Parakeet TDT 0.6B v2 (English-only) on CUDA via `onnx-asr` **(spike)** | Spike also tries v3. Fallback: `faster-whisper` with `distil-large-v3` |
| Cleanup | Ollama; candidates `qwen3:4b`, `qwen3:1.7b`, `llama3.2:3b` **(spike)** | Pass `"think": false` for Qwen3; `keep_alive: -1` so it stays loaded; warm up both models at startup |
| Paste | Save clipboard → set text → Ctrl+V → restore clipboard | Per-app fallback (typed input) for apps where Ctrl+V fails **(spike)**. Can't paste into apps running as admin — show a friendly error |
| Context | Foreground window title + process name (Win32 via `ctypes`) | Stored with each history entry only. Using it to change tone per app is a later feature |
| Storage | SQLite in `%APPDATA%\LocalFlow` | Numbered migration files from the first version. The LocalFlow Dev build uses `%APPDATA%\LocalFlow Dev` |

**Hotkey state machine (design defaults; spike S3 sets the final key and timings):**
- Key down → start recording immediately (no perceived lag).
- Released after ≥ 250 ms → push-to-talk finished → process.
- Released before 250 ms → wait up to 350 ms for a second tap. Second tap → hands-free (keep recording). No second tap → discard (accidental tap).
- In hands-free, the next tap finishes. Esc cancels in any state.
- Recordings shorter than ~0.3 s or silent → discard without calling the models.
- Default hotkey: something unlikely to clash with other apps (Right Ctrl or Ctrl+Win are the candidates); configurable.

**Cleanup guardrails:**
- Wrap the transcript in tags in the prompt; instruct "output only the cleaned text".
- If the LLM errors, times out (~3 s), or returns something wildly different in length from the input, paste the **raw** transcript instead. Never lose what I said.
- Skip the LLM for very short utterances (≤ 3 words) — just capitalise and punctuate.
- **Eval set:** 30 recorded utterances in `eval/audio/` with ideal output in `eval/cases.jsonl` (plain, fillers, self-corrections, lists, questions/commands that must not be obeyed, technical words). `uv run --project engine eval` scores cleanup against it and must pass before any change to the prompt or model is merged.

**WebSocket events (engine → UI):** `state` (`idle | listening | processing | done | error | cancelled`), `level` (0–1 audio level), `result` (history entry), `error` (message).

**REST:** `GET /history?q=&cursor=`, `DELETE /history/{id}`, `GET /stats`, `GET/PUT /settings`, `GET /health` (models loaded, GPU detected, Ollama reachable).

**One contract:** every request, response and event is a Pydantic model. Export the OpenAPI and JSON schemas and generate TypeScript types into `app/src/api/generated/` with `openapi-typescript`. CI fails if the generated types are out of date; nobody edits them by hand.

**History schema:** `id, created_at, raw_text, clean_text, app_name, window_title, duration_ms, word_count, stt_ms, llm_ms, status (ok | raw_fallback | failed)`.

### App shell (Tauri 2 + React + TypeScript + Vite + Tailwind + shadcn/ui)

- Starts the Python engine as a sidecar (in development via `uv run`, in production a bundled exe) and shows a health screen if `/health` reports problems (no GPU, Ollama not running, model missing).
- **Mock engine mode:** `pnpm --dir app dev:mock` runs the React UI in a normal browser against a fake API with scripted events. This is how Playwright, the ui-reviewer agent and impeccable see the screens, so it's built before the screens.
- **Hub window** — see section 5.
- **Overlay window** — transparent, undecorated, always-on-top, skip taskbar, not focusable, click-through except over its buttons. Built exactly the way spike S1 proved.
- **Tray** — Open, Pause dictation, Quit. Launch at login via the Tauri autostart plugin.
- Electron is the fallback only if spike S1 shows Tauri's overlay can't be made non-focus-stealing.

## 5. UI/UX spec

Overall: calm, fast, premium desktop utility — think Wispr Flow, Raycast, Linear. Not a generic dashboard. Typography and spacing do the heavy lifting; colour is used sparingly. Every interaction should feel instant (optimistic UI, 150–200 ms ease-out transitions, springy pill).

The chosen visual direction is recorded in `PRODUCT.md` and `DESIGN.md` at the repo root (written with impeccable on days 7–8). Those files win over this section on colours, type, spacing and motion; this section defines what's on each screen.

**Hub window**
- Left sidebar: Home; Settings and Help pinned at the bottom.
- **Home**
  - Greeting ("Good afternoon, [name]") and a one-line hint showing the current hotkey.
  - Stats strip: words today, total words, average words per minute, current daily streak.
  - History list grouped by **Today / Yesterday / date**, newest first, infinite scroll, instant search.
  - Each entry: clean text (2-line clamp, expand on click), time, app it was dictated into.
  - Hover actions: copy, show raw transcript, delete. Entries that fell back to raw text get a subtle badge.
  - Empty state that teaches the hotkey with a small animated demo.
- **Settings**: hotkey (record-a-shortcut field with live hint), microphone picker with live level meter, cleanup on/off, LLM model, launch at login, show overlay when idle, theme, clear history, open data folder.

**Overlay pill**
- Sits bottom-centre above the taskbar on the display the cursor is on.
- **Resting** (optional, off by default): a tiny, low-opacity pill.
- **Listening**: expands smoothly; live waveform bars driven by the `level` events.
- **Hands-free**: same as listening plus ✕ (cancel) and ✓ (finish) buttons.
- **Processing**: waveform settles into a shimmer or pulsing dots.
- **Done**: brief tick, then collapses. **Error**: short red message (e.g. "Ollama isn't running"), auto-dismiss.
- Must never take keyboard focus from the app I'm dictating into.

## 6. Targets

- Release-to-text ≤ ~1.5 s for one or two sentences on the RTX 2060 (checked at the median and 95th percentile from history timings).
- VRAM ≤ ~5 GB with both models loaded.
- Zero lost dictations: every recording I finish ends up in history, even if cleanup, paste or the engine fails. (Esc, accidental taps and silent clips are deliberately discarded.)
- Fresh Windows account: download to first dictation in under 10 minutes.

## 7. Spikes (settled on the wayfinder map before any real code)

Each is a throwaway prototype in `spikes/`, timeboxed, and ends in an ADR with measured numbers. Spike code is never imported by real code.

| Spike | Question | Pass bar | If it fails |
|---|---|---|---|
| S1 Overlay focus | Can a Tauri window appear, animate and take a click without stealing focus from Notepad? | Typing keeps landing in Notepad 20 times out of 20 | Win32 no-activate / tool-window styles from Rust; then an Electron overlay |
| S2 Speech on GPU | Does Parakeet run on CUDA on this PC, and how fast? | Under 0.5 s per 10 s of speech, on the eval clips | faster-whisper with `distil-large-v3` |
| S3 Hotkey feel | Do hold and double-tap feel right with the default key and timings? | No misfires in 50 mixed presses | Change the key or thresholds |
| S4 Paste matrix | Does clipboard paste work in Notepad, Chrome, VS Code, Slack, Windows Terminal, Word and an admin window? | All except the admin window | Typed input as a per-app fallback |
| S5 Cleanup model and prompt | Which candidate model and prompt clean the eval set best? | Never answers or obeys what was said; under 0.8 s per clip | Prompt changes, or a bigger or smaller model |
| S6 Visual direction | Which of three rendered directions for Home and the pill? | One chosen, written to PRODUCT.md and DESIGN.md | Combine directions |

## 8. Milestones and build order (tracer bullets — each ticket ends with something that runs)

| Milestone | Done when | Tickets (approximate; `/to-tickets` makes the real list) |
|---|---|---|
| M0 Decisions locked | Every spike and grilling decision is an ADR | Wayfinder map only, no product code |
| M1 Works everywhere | Dictate into any app from a console window, within the 1.5 s budget | `transcribe <file.wav>` on GPU · Cleaner + guardrails + eval command · HotkeyMachine (pure, fake-clock tests) · Recorder with levels · Injector · Console app end to end |
| M2 Live and remembered | Overlay pill works over every app; history survives restarts | History store · Local API with token · WebSocket events · Generated contract · Tauri app + sidecar + health screen · Mock engine mode · Overlay states · Overlay hands-free buttons and multi-display |
| M3 Polished app | Hub, settings and tray in daily use; no known way to lose a dictation | Hub shell + themes + tokens · History grouped by day · Search + hover actions · Greeting, stats, empty state · Settings (hotkey, mic) · Settings (cleanup, model, overlay when idle, theme, launch at login, clear history, data folder) · Tray · Failure handling · Performance · Refactors from the architecture review |
| M4 v1.0 | A fresh Windows account installs and dictates in 10 minutes | Engine as one exe sidecar · First-run setup · Installer + release workflow + LocalFlow Dev builds · Clean-account install test |

## 9. Working with Claude Code

**Workflow (Matt Pocock's skills, installed with `npx skills@latest add mattpocock/skills` — not also as a plugin):**
1. `/setup-matt-pocock-skills` once: GitHub Issues, default triage labels, single-context domain docs.
2. `/wayfinder` charts a map of decision tickets from this brief (grilling, prototype and research tickets). Work it one ticket per session with `/wayfinder Work the map. Take the ticket "…"`, recording each decision as an ADR, until the map is clear.
3. `/to-spec` on the cleared map, then `/to-tickets` **in the same session**.
4. `/implement #N` for each ticket, one per fresh session, on its own `t/<number>-<name>` branch off `dev`. It uses `tdd` and `code-review` and commits; I review, test by hand and merge.
5. `/improve-codebase-architecture` at M1 (engine only) and before M4 (whole repo). `diagnosing-bugs` for anything flaky or slow. `/handoff` when stopping mid-ticket. `/triage` for new issues. `/grill-with-docs` to plan each feature after v1.0.

**Design skills and tools:**
- Anthropic **`frontend-design`** skill — picks a deliberate aesthetic before coding and avoids generic AI-looking UI.
- **impeccable** (`npx impeccable install`) — `init` (PRODUCT.md), `shape`, `document` (DESIGN.md); then `critique`, `audit` and `polish` after every UI ticket; `onboard` for empty and first-run states; `harden` for error states.
- Vercel **`web-design-guidelines`** (`npx skills add https://github.com/vercel-labs/agent-skills --skill web-design-guidelines`) — the final UI check before merging.
- **Playwright MCP** (`claude mcp add playwright -- cmd /c npx @playwright/mcp@latest`) — screenshots the UI so Claude fixes what it actually sees.
- **Context7 MCP** (`claude mcp add --scope user context7 -- cmd /c npx -y @upstash/context7-mcp`) — current docs for Tauri 2, FastAPI, Tailwind and shadcn.
- **shadcn MCP**, once `app/` exists (`claude mcp add --scope project shadcn -- cmd /c "cd app && npx shadcn@latest mcp"`) — finds and installs shadcn/ui components.
- Not used: obra/superpowers (its workflow fights Matt's), `implement-spec` (skips the per-ticket review).
- Read each third-party skill's SKILL.md before installing.

**UI review loop, for every UI ticket:** ui-reviewer agent → `/impeccable critique` → `/impeccable audit` → `/impeccable polish` → `web-design-guidelines` → fix high-impact findings, rerun tests, commit.

**UI reviewer subagent** — save as `.claude/agents/ui-reviewer.md`:

```markdown
---
name: ui-reviewer
description: Reviews UI changes visually. Use after any change to the Hub window or overlay.
---
You are a strict product designer. Start `pnpm --dir app dev:mock` if it isn't running,
then use Playwright to screenshot every changed screen in light and dark mode at 1280x800
and 900x700. Judge against PRODUCT.md and DESIGN.md at the repo root, and the screen
contents in docs/PROJECT_BRIEF.md section 5. Report concrete issues ranked by impact:
hierarchy, spacing rhythm, typography, contrast, alignment, empty/loading/error states,
motion. Do not edit code; return a prioritised fix list.
```

## 10. Repo, code quality and branches

**Layout:**

```
localflow/
  engine/      Python package (uv): src/localflow_engine, tests
  app/         Tauri 2 + React + TypeScript (pnpm workspace package)
  docs/        PROJECT_BRIEF.md, adr/, agents/ (written by Matt's setup), design/,
               release-checklist.md, dogfood.md
  eval/        audio/, cases.jsonl, record.py
  spikes/      throwaway prototypes, never imported
  scripts/     guard_push.py and other repo scripts
  .claude/     settings.json (deny rules, format hook), agents/, hooks/
  .github/     workflows/ (ci, dev-build, release), rulesets/
  CLAUDE.md, PRODUCT.md, DESIGN.md, GLOSSARY.md (created by Matt's skills as terms are settled)
```

**Quality gates:**
- Python: ruff (lint and format, line length 100), pyright strict on `src`, pytest with a `gpu` marker that CI skips. Run `pytest -m gpu` and the eval locally before merging engine tickets.
- TypeScript: strict `tsconfig`, Biome (lint and format), Vitest + Testing Library; Playwright end-to-end tests against the mock engine.
- `.gitattributes` forces LF line endings. lefthook runs the linters and type checks on commit. A Claude Code PostToolUse hook formats every file Claude saves.
- CI (GitHub Actions, `windows-latest`) runs on pull requests to `dev` and `main`, and on pushes to `dev`.
- No new dependency without a one-paragraph ADR. `CLAUDE.md` stays under ~80 lines and points here.

**Branches:**
- `main` — only versions I've run and approved. Changes only through a promotion pull request from `dev`, merged by me with a **merge commit** (never squash). Releases are tagged here.
- `dev` — the default branch. Every finished ticket, squash-merged by me from its pull request. My daily version runs from here.
- `t/<number>-<name>` — one ticket, built by Claude with `/implement`.
- `research/<name>` — wayfinder research notes.

**Locks on main:** Claude Code deny rules (no pushing to `main`, no force-push, no `gh pr merge`, no repo-setting or ruleset changes); a lefthook pre-push guard (`scripts/guard_push.py`) that refuses any push to `refs/heads/main`; optionally a GitHub ruleset requiring a pull request and green CI (free on public repos, GitHub Pro on private ones). Claude never merges anything.

**Promotion:** before promoting, I run `dev` live and work through `docs/release-checklist.md`. Any ticket that adds something a user can see also adds its check to that file.

## 11. Packaging and release

- The engine is bundled as one exe (PyInstaller; Nuitka if startup is slow) and run as the Tauri sidecar.
- Models are downloaded on first run with a progress screen, not bundled, to keep the installer small.
- First-run setup: checks the GPU, checks for Ollama (links to install it if missing), downloads models, then teaches the hotkey with a short practice.
- NSIS installer from Tauri's bundler. Unsigned for now, so Windows SmartScreen will warn.
- `release.yml` builds and publishes the installer when a `v*` tag is pushed, and refuses tags that aren't on `main`.
- `dev-build.yml` builds a **LocalFlow Dev** installer on every push to `dev` and uploads it as the `localflow-dev-setup` artifact. It has its own app identifier, name and data folder, so it installs next to the real app. Only one can run at a time, because both use the hotkey.
