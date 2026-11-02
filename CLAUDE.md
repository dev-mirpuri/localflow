# LocalFlow

LocalFlow is a free, fully local, English-only dictation app for Windows. Press a global hotkey in any app, speak, and cleaned-up text lands at the cursor, with speech recognition (Parakeet) and cleanup (a small Ollama LLM) running on the GPU and no cloud. A Python engine does the work behind a `127.0.0.1` API, and a Tauri 2 shell provides the Hub window, overlay pill and tray. [docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md) is the source of truth for scope and design; read it before any scope, architecture or UI decision.

## Layout

```
engine/    Python 3.12 package (uv): src/localflow_engine, tests
app/       Tauri 2 + React + TypeScript, pnpm workspace package (not created yet)
docs/      PROJECT_BRIEF.md, adr/
eval/      recorded utterances for scoring cleanup
spikes/    throwaway prototypes
scripts/   repo scripts, including the pre-push guard
```

## Commands

Setup, from the repo root:

```powershell
pnpm install
uv sync --project engine
```

Engine, from `engine/`:

```powershell
uv run localflow-engine    # dev: run the engine (currently a stub)
uv run pytest              # test, skipping GPU tests
uv run pytest -m gpu       # test, GPU only; exit code 5 means no GPU tests exist yet
uv run ruff check .        # lint
uv run ruff format .       # format
uv run pyright             # type check
```

TypeScript and hooks, from the repo root:

```powershell
pnpm exec biome check .          # lint and format check
pnpm exec biome check --write .  # lint and format, applying fixes
pnpm exec lefthook run pre-commit
```

`app/` has no dev or test commands until it exists; add them here when it does.

Use `pnpm dlx` for one-off packages. `npx` fails in this repo because `package.json` requires pnpm through `devEngines`, including where the brief's setup commands use it.

## Rules

- **Tests first.** Write the failing test, see it go red, then write the code.
- **Dependencies:** add one only with a one-paragraph ADR in `docs/adr/`, in the same change.
- **Generated code:** never edit `app/src/api/generated` by hand. Change the engine's Pydantic models and regenerate.
- **Shell:** write and run commands in PowerShell.
- **Current docs:** use the Context7 MCP for Tauri 2, FastAPI, Tailwind and shadcn, before writing code against them.
- **Spikes:** `spikes/` is throwaway. Real code never imports from it; carry results over through an ADR.
- **Branches:** work on dev and ticket branches only; never push to, merge into or rebase main.
