# LocalFlow

Free, fully local dictation for Windows. See [the project brief](docs/PROJECT_BRIEF.md).

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
| Lint | `uv run ruff check .` |
| Format | `uv run ruff format .` |
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
