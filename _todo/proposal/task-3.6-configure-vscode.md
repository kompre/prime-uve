# Task 3.6: Implement `prime-uve configure vscode`

**Phase**: 3 (CLI Commands)
**Priority**: Low (optional convenience feature)
**Estimated Complexity**: Low
**Status**: Proposal

## Objective

Implement the `prime-uve configure vscode` command to automatically update VS Code workspace settings with the correct Python interpreter path from the external venv.

## Dependencies

**Requires**:
- Task 1.1: Path Hashing System ✅
- Task 1.3: .env.uve File Management ✅
- Task 1.4: Project Detection ✅
- Task 3.1: CLI Framework Setup ⏳

**Blocks**:
- None (independent of other commands)

## Background

VS Code needs to know where the Python interpreter is located. When using external venvs, users must manually configure this in their workspace settings. This command automates that process by:
1. Finding the current project's venv path from `.env.uve`
2. Locating or creating a `.code-workspace` file
3. Updating `python.defaultInterpreterPath` setting
4. Preserving other workspace settings

This makes the external venv workflow seamless for VS Code users.

## Requirements

### Functional Requirements

1. **Find Venv Path**:
   - Read `.env.uve` from current project
   - Parse and expand `UV_PROJECT_ENVIRONMENT`
   - Error if not initialized with prime-uve

2. **Locate Workspace File**:
   - Look for `*.code-workspace` in project root
   - If none found, offer to create one
   - If multiple found, ask user which to update
   - Default name: `<project_name>.code-workspace`

3. **Update Workspace Settings**:
   - Parse existing JSON (preserve formatting)
   - Update `python.defaultInterpreterPath`
   - Path format:
     - Unix: `<venv>/bin/python`
     - Windows: `<venv>/Scripts/python.exe`
   - Preserve other settings
   - Create settings object if missing

4. **Workspace File Structure**:
   ```json
   {
     "folders": [
       {"path": "."}
     ],
     "settings": {
       "python.defaultInterpreterPath": "/path/to/venv/bin/python"
     }
   }
   ```

5. **Safety**:
   - Backup workspace file before modification
   - Ask before overwriting existing interpreter setting
   - `--force` flag to skip confirmation
   - Validate JSON after update

6. **Output**:
   - Confirm workspace file updated
   - Show interpreter path
   - Suggest reloading VS Code window

### Non-Functional Requirements

- **Correctness**: Valid JSON output
- **Safety**: Don't corrupt workspace files
- **Usability**: Clear instructions for VS Code reload

## Implementation Plan

### 1. Command Structure

```python
# src/prime_uve/cli/configure.py
"""prime-uve configure commands."""
import json
import click
from pathlib import Path

from prime_uve.cli import output, errors, options
from prime_uve.core.paths import expand_path_variables
from prime_uve.core.project import find_project_root, get_project_metadata
from prime_uve.core.env_file import find_env_file, get_venv_path


@click.group()
def configure():
    """Configure editor and IDE settings."""
    pass


@configure.command()
@click.option("--force", is_flag=True, help="Overwrite existing interpreter setting without asking")
@click.option("--workspace", type=click.Path(), help="Path to .code-workspace file (auto-detect if not specified)")
@options.common_options
@click.pass_context
def vscode(ctx: click.Context, force: bool, workspace: str | None, yes: bool, dry_run: bool) -> None:
    """Update VS Code workspace settings with venv path.

    Automatically configures VS Code to use the external venv by updating
    the python.defaultInterpreterPath setting in your .code-workspace file.

    Examples:
        prime-uve configure vscode              Auto-detect workspace file
        prime-uve configure vscode --force      Overwrite existing setting
        prime-uve configure vscode --workspace my.code-workspace
    """
    verbose = ctx.obj.get("verbose", False)

    try:
        # 1. Find project root
        project_root = find_project_root()
        if not project_root:
            raise errors.UserError(
                "Not in a Python project",
                hint="Navigate to a project directory"
            )

        metadata = get_project_metadata(project_root)
        output.verbose(f"Project: {metadata.name}")

        # 2. Get venv path
        env_file = find_env_file(project_root)
        if not env_file.exists():
            raise errors.UserError(
                "No .env.uve file found",
                hint="Run 'prime-uve init' first"
            )

        venv_path_raw = get_venv_path(env_file, expand=False)
        if not venv_path_raw:
            raise errors.UserError(
                "No UV_PROJECT_ENVIRONMENT in .env.uve",
                hint="Run 'prime-uve init' to set up venv"
            )

        venv_path = expand_path_variables(venv_path_raw)
        output.verbose(f"Venv path: {venv_path}")

        # 3. Determine interpreter path
        interpreter_path = _get_interpreter_path(venv_path)
        output.verbose(f"Interpreter: {interpreter_path}")

        # 4. Find or create workspace file
        if workspace:
            workspace_file = Path(workspace)
            if not workspace_file.exists():
                raise errors.UserError(f"Workspace file not found: {workspace_file}")
        else:
            workspace_file = _find_or_create_workspace_file(
                project_root, metadata.name, yes, dry_run
            )

        output.verbose(f"Workspace file: {workspace_file}")

        # 5. Load existing workspace config
        if workspace_file.exists():
            with open(workspace_file, "r") as f:
                config = json.load(f)
        else:
            config = {
                "folders": [{"path": "."}],
                "settings": {}
            }

        # 6. Check if interpreter already set
        existing_interpreter = config.get("settings", {}).get("python.defaultInterpreterPath")
        if existing_interpreter and existing_interpreter != str(interpreter_path):
            if not force and not yes:
                output.warning(f"Existing interpreter: {existing_interpreter}")
                output.warning(f"New interpreter: {interpreter_path}")
                if not click.confirm("Overwrite existing interpreter setting?"):
                    output.info("Aborted")
                    return

        # 7. Update config
        if "settings" not in config:
            config["settings"] = {}

        config["settings"]["python.defaultInterpreterPath"] = str(interpreter_path)

        # 8. Write updated config
        if dry_run:
            output.info("Dry run - would update:")
            output.info(f"  Workspace: {workspace_file}")
            output.info(f"  Interpreter: {interpreter_path}")
            return

        # Backup original
        if workspace_file.exists():
            backup = workspace_file.with_suffix(".code-workspace.bak")
            workspace_file.rename(backup)
            output.verbose(f"Backup created: {backup}")

        # Write new config
        with open(workspace_file, "w") as f:
            json.dump(config, f, indent=2)
            f.write("\n")  # Trailing newline

        output.success(f"Updated workspace file: {workspace_file}")
        output.info(f"Interpreter: {interpreter_path}")
        output.info("")
        output.info("Please reload VS Code window for changes to take effect:")
        output.info("  Command Palette (Ctrl+Shift+P) → 'Reload Window'")

    except errors.CliError:
        raise
    except Exception as e:
        errors.handle_error(e, verbose)


def _get_interpreter_path(venv_path: Path) -> Path:
    """Get interpreter path for platform."""
    import sys

    if sys.platform == "win32":
        return venv_path / "Scripts" / "python.exe"
    else:
        return venv_path / "bin" / "python"


def _find_or_create_workspace_file(
    project_root: Path,
    project_name: str,
    yes: bool,
    dry_run: bool
) -> Path:
    """Find existing workspace file or create new one."""
    # Look for existing .code-workspace files
    workspace_files = list(project_root.glob("*.code-workspace"))

    if len(workspace_files) == 0:
        # No workspace file, create one
        workspace_file = project_root / f"{project_name}.code-workspace"

        if not yes and not dry_run:
            if not click.confirm(f"Create workspace file: {workspace_file.name}?"):
                raise errors.UserError("Aborted")

        return workspace_file

    elif len(workspace_files) == 1:
        # One workspace file found, use it
        return workspace_files[0]

    else:
        # Multiple workspace files, ask user
        output.warning("Multiple workspace files found:")
        for i, wf in enumerate(workspace_files, 1):
            output.info(f"  {i}. {wf.name}")

        if yes:
            # Use first one
            return workspace_files[0]

        choice = click.prompt(
            "Which file to update? (number or filename)",
            type=str
        )

        # Try to parse as number
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(workspace_files):
                return workspace_files[idx]
        except ValueError:
            pass

        # Try to find by name
        for wf in workspace_files:
            if wf.name == choice or str(wf) == choice:
                return wf

        raise errors.UserError(f"Invalid choice: {choice}")
```

### 2. Testing

```python
# tests/cli/test_configure.py
"""Test prime-uve configure commands."""
import json
import pytest
from pathlib import Path

from prime_uve.cli.main import cli


def test_configure_vscode_basic(isolated_cli, tmp_path):
    """Test basic vscode configuration."""
    # Setup
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text('[project]\nname="test"')

    venv = tmp_path / "venvs" / "test"
    venv.mkdir(parents=True)

    env_file = project / ".env.uve"
    env_file.write_text(f"UV_PROJECT_ENVIRONMENT={venv}")

    # Test
    result = isolated_cli.invoke(
        cli,
        ["configure", "vscode", "--yes"],
        input="y\n"
    )

    assert result.exit_code == 0

    # Check workspace file created
    workspace_files = list(project.glob("*.code-workspace"))
    assert len(workspace_files) == 1

    # Check content
    with open(workspace_files[0]) as f:
        config = json.load(f)

    assert "settings" in config
    assert "python.defaultInterpreterPath" in config["settings"]
    assert str(venv) in config["settings"]["python.defaultInterpreterPath"]


def test_configure_vscode_existing_workspace(isolated_cli, tmp_path):
    """Test updating existing workspace file."""
    # Setup
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text('[project]\nname="test"')

    venv = tmp_path / "venvs" / "test"
    venv.mkdir(parents=True)

    env_file = project / ".env.uve"
    env_file.write_text(f"UV_PROJECT_ENVIRONMENT={venv}")

    # Create existing workspace
    workspace_file = project / "test.code-workspace"
    workspace_file.write_text(json.dumps({
        "folders": [{"path": "."}],
        "settings": {"editor.tabSize": 4}
    }))

    # Test
    result = isolated_cli.invoke(cli, ["configure", "vscode"])
    assert result.exit_code == 0

    # Check settings preserved
    with open(workspace_file) as f:
        config = json.load(f)

    assert config["settings"]["editor.tabSize"] == 4
    assert "python.defaultInterpreterPath" in config["settings"]


def test_configure_vscode_overwrite_confirmation(isolated_cli, tmp_path):
    """Test confirmation when overwriting existing interpreter."""
    # Setup with existing interpreter
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text('[project]\nname="test"')

    venv = tmp_path / "venvs" / "test"
    venv.mkdir(parents=True)

    env_file = project / ".env.uve"
    env_file.write_text(f"UV_PROJECT_ENVIRONMENT={venv}")

    workspace_file = project / "test.code-workspace"
    workspace_file.write_text(json.dumps({
        "folders": [{"path": "."}],
        "settings": {"python.defaultInterpreterPath": "/old/path/python"}
    }))

    # Test abort
    result = isolated_cli.invoke(
        cli,
        ["configure", "vscode"],
        input="n\n"
    )
    assert result.exit_code == 0
    assert "Aborted" in result.output


def test_configure_vscode_force(isolated_cli, tmp_path):
    """Test --force flag skips confirmation."""
    # Setup
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text('[project]\nname="test"')

    venv = tmp_path / "venvs" / "test"
    venv.mkdir(parents=True)

    env_file = project / ".env.uve"
    env_file.write_text(f"UV_PROJECT_ENVIRONMENT={venv}")

    workspace_file = project / "test.code-workspace"
    workspace_file.write_text(json.dumps({
        "folders": [{"path": "."}],
        "settings": {"python.defaultInterpreterPath": "/old/path"}
    }))

    # Test
    result = isolated_cli.invoke(cli, ["configure", "vscode", "--force"])
    assert result.exit_code == 0

    with open(workspace_file) as f:
        config = json.load(f)

    assert str(venv) in config["settings"]["python.defaultInterpreterPath"]


def test_configure_vscode_not_initialized(isolated_cli, tmp_path):
    """Test error when project not initialized."""
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").touch()

    result = isolated_cli.invoke(cli, ["configure", "vscode"])
    assert result.exit_code == 1
    assert "No .env.uve file" in result.output


def test_configure_vscode_dry_run(isolated_cli, tmp_path):
    """Test --dry-run flag."""
    # Setup
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text('[project]\nname="test"')

    venv = tmp_path / "venvs" / "test"
    venv.mkdir(parents=True)

    env_file = project / ".env.uve"
    env_file.write_text(f"UV_PROJECT_ENVIRONMENT={venv}")

    # Test
    result = isolated_cli.invoke(
        cli,
        ["configure", "vscode", "--dry-run", "--yes"]
    )

    assert result.exit_code == 0
    assert "Dry run" in result.output

    # No workspace file created
    assert len(list(project.glob("*.code-workspace"))) == 0
```

## Acceptance Criteria

### Must Have

- ✅ Finds venv path from .env.uve
- ✅ Locates existing .code-workspace file
- ✅ Creates .code-workspace if none exists
- ✅ Updates python.defaultInterpreterPath
- ✅ Preserves other workspace settings
- ✅ Correct interpreter path for platform (bin/python vs Scripts/python.exe)
- ✅ Asks before overwriting existing interpreter
- ✅ `--force` skips confirmation
- ✅ `--dry-run` shows changes without applying
- ✅ Valid JSON output
- ✅ Backup original workspace file
- ✅ Clear instructions to reload VS Code

### Should Have

- ✅ Handle multiple workspace files (ask user)
- ✅ `--workspace` flag to specify file
- ✅ Error if not initialized
- ✅ Verbose mode shows details

### Nice to Have

- Auto-reload VS Code window (if possible)
- Configure other VS Code settings (linting, formatting)
- Support other editors (PyCharm, etc.)

## Example Usage

### Basic Usage
```bash
$ cd my-project
$ prime-uve init
$ prime-uve configure vscode
Create workspace file: my-project.code-workspace? [y/N]: y
✓ Updated workspace file: /path/to/my-project/my-project.code-workspace
ℹ Interpreter: /home/user/prime-uve/venvs/my-project_a1b2c3d4/bin/python

ℹ Please reload VS Code window for changes to take effect:
ℹ   Command Palette (Ctrl+Shift+P) → 'Reload Window'
```

### Overwrite Existing
```bash
$ prime-uve configure vscode
⚠ Existing interpreter: /usr/bin/python3
⚠ New interpreter: /home/user/prime-uve/venvs/my-project_a1b2c3d4/bin/python
Overwrite existing interpreter setting? [y/N]: y
✓ Updated workspace file
```

### Force Update
```bash
$ prime-uve configure vscode --force
✓ Updated workspace file: my-project.code-workspace
ℹ Interpreter: /home/user/prime-uve/venvs/my-project_a1b2c3d4/bin/python
```

### Multiple Workspace Files
```bash
$ prime-uve configure vscode
⚠ Multiple workspace files found:
ℹ   1. dev.code-workspace
ℹ   2. prod.code-workspace
Which file to update? (number or filename): 1
✓ Updated workspace file: dev.code-workspace
```

## Success Metrics

- ✅ All unit tests pass (target: 8+ tests)
- ✅ 100% coverage of configure command
- ✅ Valid JSON output
- ✅ Works on Windows and Unix
- ✅ Doesn't corrupt workspace files
- ✅ Clear user instructions

## Future Enhancements

1. **Other Editors**: Support PyCharm, Sublime Text, etc.
2. **More Settings**: Configure linting, formatting, testing
3. **Auto-Reload**: Trigger VS Code reload via IPC (if possible)
4. **Settings Sync**: Sync settings across workspace files
5. **Template Support**: Apply workspace templates

## References

- Architecture Design: `_todo/pending/architecture-design.md` (Section 6.5)
- [VS Code Workspace Settings](https://code.visualstudio.com/docs/editor/workspaces)

## Notes

- This is a convenience feature, not essential
- VS Code can also auto-detect venvs, but this is more explicit
- Workspace files are useful for multi-folder workspaces
- Consider adding to documentation as optional step after init
