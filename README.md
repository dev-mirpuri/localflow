# LocalFlow

Free, fully local dictation for Windows. See [the project brief](docs/PROJECT_BRIEF.md).

## Prerequisites

[uv](https://docs.astral.sh/uv/), [pnpm](https://pnpm.io/) and [Node.js](https://nodejs.org/).

## Setup

```sh
pnpm install            # also installs the git hooks
uv sync --project engine
```

## Dev commands

Run the engine commands from `engine/`:

| Task | Command |
|---|---|
| Lint | `uv run ruff check .` |
| Format | `uv run ruff format .` |
| Type check | `uv run pyright` |
| Test (no GPU) | `uv run pytest` |
| Test (GPU only) | `uv run pytest -m gpu` |

Run the TypeScript commands from the repo root:

| Task | Command |
|---|---|
| Lint and format check | `pnpm exec biome check .` |
| Lint and format, applying fixes | `pnpm exec biome check --write .` |

Run the pre-commit checks on staged files, also from the root, with `pnpm exec lefthook run pre-commit`.
