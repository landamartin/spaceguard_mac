# Agent instructions (SpaceGuard)

## Before substantive work

1. Read [`docs/SPEC.md`](docs/SPEC.md) for behavior and non-goals.
2. Skim [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) for acceptance-style checks.
3. Optionally maintain a **local** `docs/AGENT_PROGRESS.md` (not in git; see [`docs/AGENT_PROGRESS.md.example`](docs/AGENT_PROGRESS.md.example)) for session notes.

## Commands

- Install deps: `uv sync --all-groups` (see [`README.md`](README.md) if install fails or you reuse an existing PySide6).
- Run app: `uv run python -m spaceguard`.
- Tests: `uv run pytest`.
- Lint: `uv run ruff check src tests` and `uv run ruff format --check src tests`.

## Discipline

- Keep diffs focused; avoid unrelated refactors.
- Prefer extending existing modules over adding parallel implementations.

## Known caveats

- **PySide6**: Large wheels; see README for disk space and reusing an existing install.
- **Launch Agent**: Paths must match how the user runs the app (venv vs bundled `.app`).
- **Qt Widgets**: This project uses Qt Widgets for the menu bar UI (not QML).
