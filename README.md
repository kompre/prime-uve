# prime-uve

[![PyPI version](https://badge.fury.io/py/prime-uve.svg)](https://badge.fury.io/py/prime-uve)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://github.com/kompre/prime-uve/actions/workflows/test.yml/badge.svg)](https://github.com/kompre/prime-uve/actions/workflows/test.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

A thin wrapper for [uv](https://github.com/astral-sh/uv) that provides seamless external venv management with automatic environment loading.

## Why prime-uve?

Some scenarios require virtual environments outside the project directory:

- **Network shares**: Project on network drive, but venv must be local for performance
- **Multiple workspaces**: Same project cloned in different locations needs separate venvs
- **Centralized management**: All venvs in one location for easy cleanup
- **Cross-platform teams**: Same `.env.uve` works on Linux, macOS, and Windows

uv can use external venvs via the `UV_PROJECT_ENVIRONMENT` variable, but requires it to be set for every command. The `uve` command automates this by running `uv run --env-file .env.uve -- uv [args]` with automatic `.env.uve` discovery and `${PRIMEUVE_VENVS_PATH}` injection.

As a side effect, this also loads any other environment variables you set in `.env.uve`.

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

## Shell Integration

### `prime-uve activate`
Output activation commands for current shell:

```bash
eval "$(prime-uve activate)"  # Activate venv in current shell (bash/zsh)
```

### `prime-uve shell`
Spawn new shell with venv activated:

```bash
prime-uve shell               # Auto-detect shell
prime-uve shell --shell bash  # Force specific shell
```

## Utilities

### `prime-uve dir`
Open venvs directory in file explorer:

```bash
prime-uve dir  # Opens platform-specific venvs cache directory
```

### `prime-uve register`
Manually register current project in cache (rarely needed):

```bash
prime-uve register  # Register current project from existing .env.uve
```

## VS Code Integration

Configure VS Code workspace files with your external venv using platform-generic variables.

### Basic Usage

```bash
cd your-project/
prime-uve configure vscode
```

Updates (or creates) `.code-workspace` file with interpreter path:
- Linux: `${userHome}/.cache/prime-uve/venvs/project_hash/bin/python`
- macOS: `${userHome}/Library/Caches/prime-uve/venvs/project_hash/bin/python`
- Windows: `${env:LOCALAPPDATA}/prime-uve/Cache/venvs/project_hash/Scripts/python.exe`

### Platform-Specific Workspaces

For teams working across different operating systems:

```bash
# On Linux machine
prime-uve configure vscode --suffix
# Creates: myproject.linux.code-workspace

# On macOS machine
prime-uve configure vscode --suffix
# Creates: myproject.macos.code-workspace

# On Windows machine
prime-uve configure vscode --suffix
# Creates: myproject.windows.code-workspace
```

All workspace files can coexist in version control. Team members open the one for their platform.

### Advanced Options

```bash
# Merge settings from another workspace
prime-uve configure vscode --suffix --merge myproject.code-workspace

# Use absolute paths instead of variables (not recommended)
prime-uve configure vscode --expand

# Set default workspace for future merges
prime-uve configure vscode --export-as-default myproject.code-workspace

# Preview changes without applying
prime-uve configure vscode --dry-run

# Suppress output, get JSON result
prime-uve configure vscode --json
```

### Options Reference

| Option | Description |
|--------|-------------|
| `--suffix [VALUE]` | Create platform-specific workspace (auto-detects OS if no value) |
| `--merge [FILE]` | Merge settings from another workspace (requires --suffix) |
| `--expand` | Use absolute paths instead of VS Code variables |
| `--export-as-default [FILE]` | Save workspace as default in `.env.uve` |
| `--workspace PATH` | Specific workspace file to update |
| `--yes` | Skip confirmation prompts |
| `--dry-run` | Preview changes without applying |
| `--json` | Output result as JSON |

## Path Configuration

`.env.uve` uses `${PRIMEUVE_VENVS_PATH}` variable for cross-platform compatibility:

```bash
UV_PROJECT_ENVIRONMENT="${PRIMEUVE_VENVS_PATH}/myproject_abc123"
```

This variable automatically expands to platform-specific cache locations:

| Platform | Default Path |
|----------|-------------|
| Linux | `~/.cache/prime-uve/venvs` |
| macOS | `~/Library/Caches/prime-uve/venvs` |
| Windows | `%LOCALAPPDATA%\prime-uve\Cache\venvs` |

Override with `PRIMEUVE_VENVS_PATH` environment variable if needed.

The path includes:
- **Project name** from `pyproject.toml`
- **Short hash** derived from project path (ensures uniqueness)

## How It Works

### The `uve` Command

`uve` is almost an alias for `uv run --env-file .env.uve -- uv [args]` with two enhancements:

1. **Automatic `.env.uve` discovery**: Searches current directory and walks up parent directories
2. **Platform-aware variable injection**: Sets `PRIMEUVE_VENVS_PATH` to platform-specific cache location

**Example workflow** when you run `uve sync`:

1. `uve` finds `.env.uve` (walks up directory tree from current location)
2. Injects `PRIMEUVE_VENVS_PATH` environment variable:
   - Linux: `~/.cache/prime-uve/venvs`
   - macOS: `~/Library/Caches/prime-uve/venvs`
   - Windows: `%LOCALAPPDATA%\prime-uve\Cache\venvs`
3. Runs: `uv run --env-file .env.uve -- uv sync`
4. uv reads `UV_PROJECT_ENVIRONMENT=${PRIMEUVE_VENVS_PATH}/project_hash` from `.env.uve`
5. Variable expands to actual path (e.g., `~/.cache/prime-uve/venvs/project_hash`)
6. uv creates/uses venv at the expanded external location

This means you can run `uve` commands from any subdirectory within your project, and the same `.env.uve` file works across different platforms and users.

### The `prime-uve` Interface

`prime-uve` provides commands to:

**Setup and initialization**:
- `prime-uve init` - Creates `.env.uve` with `UV_PROJECT_ENVIRONMENT=${PRIMEUVE_VENVS_PATH}/project_hash`

**Venv tracking** (cache at `~/.local/share/prime-uve/cache.json` on Linux):
- `prime-uve list` - Shows all venvs with validation status
- `prime-uve prune` - Removes venvs (--orphan for deleted projects, --all for everything)
- `prime-uve register` - Manually add project to cache

**Shell integration**:
- `prime-uve activate` - Outputs activation commands for current shell
- `prime-uve shell` - Spawns new shell with venv activated

**IDE integration**:
- `prime-uve configure vscode` - Updates workspace files with platform-generic interpreter paths

**Utilities**:
- `prime-uve dir` - Opens venvs cache directory in file explorer

### Platform-Aware Defaults

The `PRIMEUVE_VENVS_PATH` variable automatically uses platform-specific cache locations following OS conventions:

| Platform | Environment Variable | Default Location |
|----------|---------------------|------------------|
| Linux | `XDG_CACHE_HOME` | `~/.cache/prime-uve/venvs` |
| macOS | - | `~/Library/Caches/prime-uve/venvs` |
| Windows | `LOCALAPPDATA` | `%LOCALAPPDATA%\prime-uve\Cache\venvs` |

Override by setting `PRIMEUVE_VENVS_PATH` environment variable before running `uve` commands.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Credits

Built on top of [uv](https://github.com/astral-sh/uv) by Astral.
