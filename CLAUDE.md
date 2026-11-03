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

# LocalFlow

LocalFlow is a free, fully local, English-only dictation app for Windows. Press a global hotkey in any app, speak, and cleaned-up text lands at the cursor, with speech recognition (Parakeet) and cleanup (a small Ollama model) running on the GPU. An Electron app (oval, history window, tray) starts the Python engine. [docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md) is the source of truth for scope and design; read it before any scope, architecture or UI decision.

## Layout

```
engine/     Python 3.12 package (uv): src/localflow_engine, tests
app/        Electron app (electron-vite react-ts template, npm)
docs/       PROJECT_BRIEF.md, adr/
eval/       recorded utterances for scoring cleanup
.githooks/  pre-commit, pre-push
```

## Commands

Run in PowerShell. Setup, from the repo root:

```powershell
uv sync --project engine
npm ci --prefix app
git config core.hooksPath .githooks
```

From `engine/`:

```powershell
uv run ruff check . ../eval    # lint
uv run ruff format . ../eval   # format
uv run pytest                  # test, skipping GPU and Windows-input tests
uv run pytest -m gpu           # GPU tests only; -m windows for Windows-input tests
```

From `app/`:

```powershell
npm run dev        # run in development
npm run lint       # ESLint
npm run format     # Prettier
npm run typecheck  # type check
```

## Rules

- **Tests first.** Where the rule above calls for a test, write it, see it go red, then write the code.
- **Current docs:** use the Context7 MCP for Electron, electron-vite and Tailwind before writing code against them.
- **Spikes:** `spikes/` is throwaway. Real code never imports from it; carry results over through an ADR in `docs/adr/`.
- **Branches:** work on dev and ticket branches only; never push to, merge into or rebase main.
