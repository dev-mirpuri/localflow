"""PostToolUse hook: format the file Claude just saved.

Reads the hook JSON from stdin and formats tool_input.file_path by extension.
Exit 2 shows a formatter failure to Claude; the file stays saved either way.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUFF_COMMAND = ["uv", "run", "--project", "engine", "ruff", "format"]
BIOME_COMMAND = ["pnpm", "biome", "format", "--write"]
FORMATTERS = {
    ".py": RUFF_COMMAND,
    ".ts": BIOME_COMMAND,
    ".tsx": BIOME_COMMAND,
    ".json": BIOME_COMMAND,
    ".css": BIOME_COMMAND,
}


def main() -> None:
    payload = json.load(sys.stdin)
    file_path = payload.get("tool_input", {}).get("file_path")
    if not file_path:
        return

    command = FORMATTERS.get(Path(file_path).suffix.lower())
    if command is None:
        return

    # pnpm is a .cmd shim on Windows, which subprocess only finds by full path.
    executable = shutil.which(command[0]) or command[0]
    result = subprocess.run(
        [executable, *command[1:], file_path],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        print(f"format.py: could not format {file_path}", file=sys.stderr)
        print(result.stdout + result.stderr, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
