# Task 3.2: Implement `prime-uve init`

**Phase**: 3 (CLI Commands)
**Priority**: High (core command)
**Estimated Complexity**: Medium
**Status**: Proposal

## Objective

Implement the `prime-uve init` command to initialize a Python project with an external virtual environment. This command sets up the `.env.uve` file, creates the venv directory, updates the cache, and optionally runs `uv sync`.

## Dependencies

**Requires**:
- Task 1.1: Path Hashing System ✅
- Task 1.2: Cache System ✅
- Task 1.3: .env.uve File Management ✅
- Task 1.4: Project Detection ✅
- Task 3.1: CLI Framework Setup ⏳

**Blocks**:
- None (independent of other commands)

## Background

`prime-uve init` is the entry point for users to start using external venvs. It:
1. Detects the current Python project
2. Generates a deterministic venv path using project name + hash
3. Creates `.env.uve` with `UV_PROJECT_ENVIRONMENT`
4. Adds mapping to cache
5. Creates venv directory structure
6. Optionally runs `uv sync` to initialize the venv

This is typically the first command users run in a new project.

## Requirements

### Functional Requirements

1. **Project Detection**:
   - Find project root (pyproject.toml location)
   - Error if not in a Python project
   - Error if project name cannot be determined

2. **Initialization Checks**:
   - Check if already initialized (.env.uve exists with content)
   - Warn if .env.uve exists but cache doesn't match
   - `--force` flag reinitializes even if already set up

3. **Venv Path Generation**:
   - Use `generate_venv_path()` from Task 1.1
   - Always uses `${HOME}` for cross-platform compatibility
   - Format: `${HOME}/prime-uve/venvs/{project_name}_{hash}`

4. **.env.uve Creation**:
   - Create or update .env.uve at project root
   - Write `UV_PROJECT_ENVIRONMENT=<venv_path>`
   - Preserve other variables if file exists

5. **Cache Update**:
   - Add mapping to cache
   - Store both variable form and expanded form
   - Update timestamp

6. **Venv Directory Creation**:
   - Create parent directories if needed
   - Handle permission errors gracefully

7. **Venv Initialization**:
   - Run `uv sync` to create venv (default)
   - `--no-sync` flag skips sync
   - Forward uv output to user

8. **Output**:
   - Show project name
   - Show venv path (both variable and expanded forms)
   - Confirm .env.uve created
   - Confirm cache updated
   - Show sync output if run

### Non-Functional Requirements

- **Idempotency**: Running init twice should be safe (with --force)
- **Atomicity**: Rollback on errors (remove .env.uve, cache entry)
- **Performance**: Complete in < 5 seconds (excluding uv sync)
- **Usability**: Clear error messages with suggestions

## Implementation Plan

### 1. Command Structure

```python
# src/prime_uve/cli/init.py
"""prime-uve init command."""
import click
from pathlib import Path

from prime_uve.cli import output, errors, options
from prime_uve.core.cache import Cache
from prime_uve.core.paths import generate_venv_path, expand_path_variables
from prime_uve.core.project import find_project_root, get_project_metadata
from prime_uve.core.env_file import find_env_file, write_env_file, get_venv_path


@click.command()
@click.option("--force", is_flag=True, help="Reinitialize even if already set up")
@click.option("--no-sync", is_flag=True, help="Skip running uv sync")
@click.option("--venv-dir", type=click.Path(), help="Override venv directory (for testing)")
@click.pass_context
def init(ctx: click.Context, force: bool, no_sync: bool, venv_dir: str | None) -> None:
    """Initialize external venv for current project.

    Sets up .env.uve file, creates venv directory, and runs uv sync.

    Example:
        cd /path/to/my-project
        prime-uve init
    """
    verbose = ctx.obj.get("verbose", False)

    try:
        # 1. Find project root
        output.verbose("Detecting project root...")
        project_root = find_project_root()
        if not project_root:
            raise errors.UserError(
                "Not in a Python project",
                hint="Navigate to a directory with pyproject.toml or create one with 'uv init'"
            )

        # 2. Get project metadata
        output.verbose(f"Found project root: {project_root}")
        metadata = get_project_metadata(project_root)
        project_name = metadata.name

        # 3. Check if already initialized
        env_file = find_env_file(project_root)
        existing_venv = get_venv_path(env_file, expand=False) if env_file.exists() else None

        if existing_venv and not force:
            raise errors.UserError(
                f"Project already initialized with venv: {existing_venv}",
                hint="Use --force to reinitialize"
            )

        # 4. Generate venv path
        if venv_dir:
            # Custom venv dir (for testing)
            venv_path = f"${{HOME}}/{venv_dir}/{project_name}"
        else:
            venv_path = generate_venv_path(project_root)

        venv_path_expanded = expand_path_variables(venv_path)

        output.verbose(f"Venv path: {venv_path}")
        output.verbose(f"Expanded: {venv_path_expanded}")

        # 5. Create .env.uve
        output.verbose("Creating .env.uve...")
        write_env_file(env_file, {"UV_PROJECT_ENVIRONMENT": venv_path})
        output.success(f"Created .env.uve at {env_file.parent}")

        # 6. Update cache
        output.verbose("Updating cache...")
        cache = Cache()
        cache.add_mapping(
            project_path=project_root,
            venv_path=venv_path,
            project_name=project_name
        )
        output.success("Updated cache")

        # 7. Create venv directory
        output.verbose(f"Creating venv directory at {venv_path_expanded}...")
        venv_path_expanded.mkdir(parents=True, exist_ok=True)
        output.success(f"Created venv directory")

        # 8. Run uv sync (unless --no-sync)
        if not no_sync:
            output.verbose("Running uv sync...")
            import subprocess
            result = subprocess.run(
                ["uv", "sync"],
                cwd=project_root,
                env={**os.environ, "UV_PROJECT_ENVIRONMENT": str(venv_path_expanded)}
            )
            if result.returncode != 0:
                raise errors.SystemError("uv sync failed")
            output.success("Initialized venv with uv sync")

        # Summary
        output.info("")
        output.info(f"Project: {project_name}")
        output.info(f"Venv: {venv_path}")
        output.info(f"Location: {venv_path_expanded}")
        output.info("")
        output.success("Initialization complete!")

        if no_sync:
            output.info("Run 'uv sync' to install dependencies")

    except errors.CliError:
        raise
    except Exception as e:
        errors.handle_error(e, verbose)
```

### 2. Edge Cases

#### Already Initialized (no --force)
```
Error: Project already initialized with venv: ${HOME}/prime-uve/venvs/myproject_a1b2c3d4
Hint: Use --force to reinitialize
```

#### Not in a Project
```
Error: Not in a Python project
Hint: Navigate to a directory with pyproject.toml or create one with 'uv init'
```

#### Permission Denied
```
Error: Permission denied creating venv directory
Hint: Check permissions on /home/user/prime-uve/venvs/
```

#### uv Not Available
```
Error: 'uv' command not found
Hint: Install uv from https://github.com/astral-sh/uv
```

#### Cache/Env Mismatch (with --force)
```
Warning: .env.uve exists but cache is out of sync
⚠ Reinitializing will update both .env.uve and cache
```

### 3. Rollback on Error

If any step fails, undo previous changes:
```python
def init_with_rollback():
    """Initialize with automatic rollback on error."""
    created_env_file = False
    updated_cache = False
    created_venv_dir = False

    try:
        # ... initialization steps ...
        created_env_file = True
        # ... more steps ...
        updated_cache = True
        # ... more steps ...
        created_venv_dir = True

    except Exception as e:
        # Rollback in reverse order
        if created_venv_dir:
            shutil.rmtree(venv_path_expanded, ignore_errors=True)
        if updated_cache:
            cache.remove_mapping(project_root)
        if created_env_file:
            env_file.unlink(missing_ok=True)
        raise
```

### 4. Testing

```python
# tests/cli/test_init.py
"""Test prime-uve init command."""
import pytest
from click.testing import CliRunner
from pathlib import Path

from prime_uve.cli.main import cli


def test_init_basic(isolated_cli, tmp_path):
    """Test basic initialization."""
    # Create pyproject.toml
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-project"')

    result = isolated_cli.invoke(cli, ["init", "--no-sync"])
    assert result.exit_code == 0
    assert "Created .env.uve" in result.output
    assert ".env.uve" in (tmp_path / ".env.uve").read_text()


def test_init_already_initialized(isolated_cli, tmp_path):
    """Test error when already initialized."""
    # Setup
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test"')
    env_file = tmp_path / ".env.uve"
    env_file.write_text("UV_PROJECT_ENVIRONMENT=${HOME}/venvs/test")

    # Test
    result = isolated_cli.invoke(cli, ["init"])
    assert result.exit_code == 1
    assert "already initialized" in result.output


def test_init_force(isolated_cli, tmp_path):
    """Test --force flag reinitializes."""
    # Setup
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test"')
    env_file = tmp_path / ".env.uve"
    env_file.write_text("UV_PROJECT_ENVIRONMENT=${HOME}/old/path")

    # Test
    result = isolated_cli.invoke(cli, ["init", "--force", "--no-sync"])
    assert result.exit_code == 0
    assert "prime-uve/venvs/" in env_file.read_text()  # New path


def test_init_not_in_project(isolated_cli, tmp_path):
    """Test error when not in a project."""
    result = isolated_cli.invoke(cli, ["init"])
    assert result.exit_code == 1
    assert "Not in a Python project" in result.output


def test_init_verbose(isolated_cli, tmp_path):
    """Test verbose output."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test"')

    result = isolated_cli.invoke(cli, ["--verbose", "init", "--no-sync"])
    assert result.exit_code == 0
    assert "Detecting project root" in result.output
    assert "Creating .env.uve" in result.output


def test_init_custom_venv_dir(isolated_cli, tmp_path):
    """Test --venv-dir option."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test"')

    result = isolated_cli.invoke(
        cli,
        ["init", "--venv-dir", "custom/venvs", "--no-sync"]
    )
    assert result.exit_code == 0
    env_content = (tmp_path / ".env.uve").read_text()
    assert "custom/venvs" in env_content
```

## Acceptance Criteria

### Must Have

- ✅ Detects project root correctly
- ✅ Generates deterministic venv path
- ✅ Creates .env.uve with UV_PROJECT_ENVIRONMENT
- ✅ Updates cache with mapping
- ✅ Creates venv directory structure
- ✅ Runs uv sync by default
- ✅ `--no-sync` skips uv sync
- ✅ `--force` reinitializes existing projects
- ✅ Error if not in a Python project
- ✅ Rollback on errors (atomic operation)
- ✅ Clear success/error messages
- ✅ Verbose mode shows detailed steps

### Should Have

- ✅ `--venv-dir` for custom venv location (testing)
- ✅ Preserves other variables in .env.uve
- ✅ Detects cache/env mismatches
- ✅ Summary output with project name and paths

### Nice to Have

- Progress indicator for uv sync
- Detect if uv is available before starting
- Suggest next steps after initialization

## Example Usage

### Basic Initialization
```bash
$ cd my-project
$ prime-uve init
✓ Created .env.uve at /path/to/my-project
✓ Updated cache
✓ Created venv directory
✓ Initialized venv with uv sync

ℹ Project: my-project
ℹ Venv: ${HOME}/prime-uve/venvs/my-project_a1b2c3d4
ℹ Location: /home/user/prime-uve/venvs/my-project_a1b2c3d4

✓ Initialization complete!
```

### Reinitialize with Force
```bash
$ prime-uve init --force
⚠ Project already initialized, reinitializing...
✓ Created .env.uve at /path/to/my-project
✓ Updated cache
✓ Created venv directory
✓ Initialized venv with uv sync
✓ Initialization complete!
```

### Skip Sync
```bash
$ prime-uve init --no-sync
✓ Created .env.uve at /path/to/my-project
✓ Updated cache
✓ Created venv directory
✓ Initialization complete!
ℹ Run 'uv sync' to install dependencies
```

## Success Metrics

- ✅ All unit tests pass (target: 10+ tests)
- ✅ 100% coverage of init command
- ✅ Works on Windows, macOS, Linux
- ✅ Atomic operation (rollback on error)
- ✅ Clear error messages for common issues
- ✅ Completes in < 5 seconds (excluding uv sync)

## Future Enhancements

1. **Python Version Selection**: `--python 3.11` to specify Python version
2. **Template Support**: `--template <name>` to use predefined configs
3. **Interactive Mode**: Prompt for options if not provided
4. **Import Existing**: Detect and import manually created venvs
5. **Multi-venv**: Support multiple venvs per project (py311, py312, etc.)

## References

- Architecture Design: `_todo/pending/architecture-design.md` (Section 6.1)
- Task 1.1: Path Hashing System
- Task 1.2: Cache System
- Task 1.3: .env.uve File Management
- Task 1.4: Project Detection

## Notes

- This is the primary entry point for new users
- Error messages should be especially clear
- Consider adding examples to help text
- Should work even if uv is not installed (skip sync)
