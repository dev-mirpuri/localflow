# LocalFlow

Free, fully local dictation for Windows. See [the project brief](docs/PROJECT_BRIEF.md).

## Install

1. You need an NVIDIA GPU with at least 6 GB of memory and a current driver from [nvidia.com/drivers](https://www.nvidia.com/drivers). There is no CPU mode.
2. Install [Ollama](https://ollama.com/download) and leave it running.
3. In a terminal, run `ollama pull qwen3:1.7b` (about 1.4 GB).
4. Download `LocalFlow-<version>-setup.exe` from the [releases](https://github.com/dev-mirpuri/localflow/releases) and run it. It isn't signed, so Windows SmartScreen warns "Windows protected your PC": click **More info**, then **Run anyway**.
5. LocalFlow starts in the tray. The first time, it downloads the speech model (Parakeet, about 2.5 GB), and the oval shows "Downloading speech model…" until it's done.
6. Click where you want text, hold Right Ctrl, speak, and let go.

Settings are in `%APPDATA%\LocalFlow\config.json` (restart LocalFlow after editing), and `engine.log` beside it says what went wrong if something does.

## Prerequisites

[uv](https://docs.astral.sh/uv/) and [Node.js](https://nodejs.org/), which includes npm.

## Setup

From the repo root:

```sh
uv sync --project engine
npm ci --prefix app
git config core.hooksPath .githooks
```

The last command turns on the git hooks: `pre-commit` runs the checks below, and `pre-push` refuses any push to `main`.

## Dev commands

Run the engine commands from `engine/`:

| Task | Command |
|---|---|
| Lint | `uv run ruff check . ../eval` |
| Format | `uv run ruff format . ../eval` |
| Test (default, skips GPU and Windows-input tests) | `uv run pytest` |
| Test (GPU only) | `uv run pytest -m gpu` |
| Test (Windows input only) | `uv run pytest -m windows` |

Run the app commands from `app/`:

| Task | Command |
|---|---|
| Run in development | `npm run dev` |
| Lint | `npm run lint` |
| Format | `npm run format` |
| Type check | `npm run typecheck` |
| Build | `npm run build` |
| Build the installer (Engine first, then `dist\LocalFlow-<version>-setup.exe`) | `npm run build:win` |

Quit any installed LocalFlow from its tray icon before `npm run dev`; two copies would both listen for the Hotkey.

## The pages in a browser

`npm run dev` starts the whole App: the tray icon, the Engine (through `uv run`, with its data in `%APPDATA%\LocalFlow Dev`) and both windows. To work on the pages alone, run `npx electron-vite dev --rendererOnly` from `app/`; in a normal browser the pages use the Fake bridge, which gives sample Entries and cycles the Oval's states:

- History window: http://localhost:5173/history.html
- Oval: http://localhost:5173/oval.html
