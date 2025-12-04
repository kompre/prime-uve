# prime-uve

[![PyPI version](https://badge.fury.io/py/prime-uve.svg)](https://badge.fury.io/py/prime-uve)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://github.com/kompre/prime-uve/actions/workflows/test.yml/badge.svg)](https://github.com/kompre/prime-uve/actions/workflows/test.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

A thin wrapper for [uv](https://github.com/astral-sh/uv) that provides seamless external venv management with automatic environment loading.

## Why prime-uve?

For some project venv location is preferable outside the project root, on the local machine (e.g. if a project is save on a network share, venv should not be there for performance reasons). Tools like `poetry` do manage venv in a cache location, but `uv` does not *easily*: uv can read venv path from the environment variable `UV_PROJECT_ENVIRONMENT`, and the variable needs to be set for every subsequent `uv` call. Managing this manually is tedious and error-prone. 

`uv` by default does not load environment variables from a `.env`, but it can run any command loading environment variables from a `.env` file with the `--env-file <file>` flag. Therefore this syntax is valid:

```bash
uv run --env-file <.env> -- uv [command]
```

`prime-uve` automates loading `.env.uve` for every command and provides tooling to manage venvs in a centralized location outside project roots.

As a *side effect* this tool also run `uv` with any environment variables the user decide to set in the `.env.uve` file.

## Features

- **`uve` command** - Alias for `uv run --env-file .env.uve -- uv [command]`
- **`prime-uve` CLI** - Venv management with external venv locations
- **Automatic `.env.uve` discovery** - Walks up directory tree to find config
- **Cross-platform paths** - Uses expandable env variables (`$HOME`)
- **Centralized venv storage** - Keep venvs organized outside project directories
- **Orphan detection** - Track and clean up venvs from deleted projects

## Installation

Install system-wide as a CLI tool:

```bash
uv tool install prime-uve
```

## Quick Start

### 1. Initialize a project

```bash
cd your-project/
uv init # generate the pyproject.toml
prime-uve init 
```

This creates `.env.uve` with:
```bash
UV_PROJECT_ENVIRONMENT="$HOME/prime-uve/venvs/<project_name>_<hash>"
```

### 2. Use `uve` instead of `uv`

```bash
uve sync                    # Instead of: uv run --env-file .env.uve -- uv sync
uve add requests            # Instead of: uv run --env-file .env.uve -- uv add requests
uve run python script.py    # Instead of: uv run --env-file .env.uve -- uv run python script.py
```

## `.env.uve` File Lookup

The lookup logic for `.env.uve`:

1. Look for `.env.uve` in current directory
2. If not found and cwd is not project root (no `pyproject.toml`), walk up the tree

This ensures commands work correctly from any subdirectory within your project.

## Venv Management Commands

### `prime-uve list`
List all managed venvs with validation:
- Checks if projects still exist
- Verifies paths match `.env.uve` mappings
- Highlights orphaned venvs

### `prime-uve prune`
Remove venvs from cache:
- `--all` - Clean everything
- `--orphan` - Clean only orphan venvs (deleted or moved projects)
- `path/to/venv` - Clean specific venv
- `--current` - Clean venv mapped to current project

<!-- ### `prime-uve activate`
Activate current project venv from `.env.uve`

### `prime-uve configure vscode`
Update `.code-workspace` file with venv path for VS Code integration -->

## Path Configuration

Venv paths use environment variables for cross-platform compatibility:

```bash
# path uses $env variables for cross-platform compatibility
UV_PROJECT_ENVIRONMENT="$HOME/prime-uve/venvs/<project_name>_<hash>"
```

The path includes:
- **Project name** - From `pyproject.toml`
- **Short hash** - Derived from project path to ensure uniqueness

## Architecture

**Current Status:** Early development phase. Core commands implemented:
- `prime-uve init` - Initialize project venv
- `prime-uve list` - List managed venvs
- `prime-uve prune` - Clean up orphaned venvs

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Credits

Built on top of [uv](https://github.com/astral-sh/uv) by Astral.
