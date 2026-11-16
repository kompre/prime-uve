# CLAUDE.md

Guidance for Claude Code in this repository. Workflow, CI and releases are
described in `CONTRIBUTING.md`.

## Project

**prime-uve** is a thin wrapper for `uv` with two commands:

1. **`uve`** - alias for `uv run --no-project --env-file .env.uve -- uv [args]`
   (`src/prime_uve/uve/wrapper.py`). `--no-project` keeps the outer `uv run`
   from syncing a local `.venv` (uv >= 0.11.17 no longer applies `--env-file`
   to its own process).
2. **`prime-uve`** - click CLI to manage venvs stored outside the project:
   `init`, `list`, `prune`, `activate`, `shell`, `dir`, `register`,
   `configure vscode` (`src/prime_uve/cli/`).

`.env.uve` holds `UV_PROJECT_ENVIRONMENT="${PRIMEUVE_VENVS_PATH}/<name>_<hash>"`.
`uve` injects `PRIMEUVE_VENVS_PATH` (platform cache dir, overridable):
Linux `~/.cache/prime-uve/venvs`, macOS `~/Library/Caches/prime-uve/venvs`,
Windows `%LOCALAPPDATA%\prime-uve\Cache\venvs`. Lookup: cwd, then walk up to
the project root (`pyproject.toml`).

## Layout

| Path | Responsibility |
|---|---|
| `core/paths.py` | venv cache location, path hashing |
| `core/env_file.py` | find / read / write `.env.uve` |
| `core/cache.py` | local project <-> venv mapping (filelock), used by `list`/`prune` to detect orphans |
| `core/project.py` | project root detection |
| `utils/` | disk usage, shell detection, venv helpers, VS Code workspace edits |
| `cli/` | one module per command, `main.py` wires them up |

## Commands

```bash
uv sync --group dev
uv run pytest tests            # 2 permission tests fail when run as root (containers); fine in CI
uv run ruff check src tests
uv run ruff format src tests   # CI runs `ruff format --check`; no bot auto-fixes, so format before committing
```

Use `uv add/remove` rather than editing dependencies by hand.

## Workflow (short version)

- Work is tracked in GitHub issues. One branch + one PR per issue, PR into `main`.
- PRs are squash-merged: the **PR title** is the commit release-please reads, so
  it must be a conventional commit (`fix(uve): ...`, `feat(list): ...`,
  `feat!: ...`). Put `Fixes #N` in the PR body.
- Never edit the version in `pyproject.toml` or `CHANGELOG.md` by hand -
  release-please owns them.
- Releases happen by merging the standing `chore(main): release X.Y.Z` PR.
