# Task 3.5: Implement `prime-uve activate`

**Phase**: 3 (CLI Commands)
**Priority**: Medium (nice-to-have feature)
**Estimated Complexity**: Medium
**Status**: Proposal

## Objective

Implement the `prime-uve activate` command to output shell-specific activation commands for the current project's venv. Also exports all environment variables from `.env.uve`, not just `UV_PROJECT_ENVIRONMENT`.

## Dependencies

**Requires**:
- Task 1.1: Path Hashing System ✅
- Task 1.3: .env.uve File Management ✅
- Task 1.4: Project Detection ✅
- Task 3.1: CLI Framework Setup ⏳

**Blocks**:
- None (independent of other commands)

## Background

While `uve` wrapper automatically uses `.env.uve` for uv commands, users sometimes need to:
1. Activate the venv manually (for non-uv Python tools)
2. Export all `.env.uve` variables to their shell session
3. Use Python directly without going through uve

`prime-uve activate` solves this by:
- Detecting the user's shell
- Reading ALL variables from `.env.uve` (not just UV_PROJECT_ENVIRONMENT)
- Outputting appropriate export commands for all variables
- Outputting the correct activation command for the detected shell

Users run: `eval "$(prime-uve activate)"`

## Requirements

### Functional Requirements

1. **Shell Detection**:
   - Auto-detect from `$SHELL` env var (Unix) or `COMSPEC` (Windows)
   - Support: bash, zsh, fish, PowerShell, cmd
   - `--shell <name>` flag for manual override
   - Error on unsupported shells

2. **Environment Variable Export**:
   - Parse ALL variables from `.env.uve`
   - Output export commands for ALL variables (not just UV_PROJECT_ENVIRONMENT)
   - Preserve variable format (don't expand during export)
   - Shell-specific export syntax

3. **Venv Path Resolution**:
   - Find `.env.uve` in current project
   - Parse `UV_PROJECT_ENVIRONMENT` path
   - Expand `${HOME}` for activation script path
   - Error if venv doesn't exist

4. **Activation Command**:
   - Output correct activation script path for shell
   - Use expanded path (venv must exist locally)
   - Format varies by shell:
     - bash/zsh: `source <path>/bin/activate`
     - fish: `source <path>/bin/activate.fish`
     - PowerShell: `& <path>\Scripts\Activate.ps1`
     - cmd: `<path>\Scripts\activate.bat`

5. **Windows HOME Handling**:
   - On Windows PowerShell, ensure `$env:HOME` is set
   - Set to `$env:USERPROFILE` if not already set
   - This ensures `${HOME}` in .env.uve works correctly

6. **Error Handling**:
   - Not in a project → clear error
   - `.env.uve` missing → suggest `prime-uve init`
   - Venv doesn't exist → suggest `uv sync`
   - Unsupported shell → list supported shells

### Non-Functional Requirements

- **Compatibility**: Works on bash, zsh, fish, PowerShell, cmd
- **Speed**: Output in < 100ms
- **Correctness**: Generated commands must work when eval'd

## Implementation Plan

### 1. Shell Detection Utility

```python
# src/prime_uve/utils/shell.py
"""Shell detection utilities."""
import os
import sys
from enum import Enum
from pathlib import Path


class Shell(Enum):
    """Supported shells."""
    BASH = "bash"
    ZSH = "zsh"
    FISH = "fish"
    POWERSHELL = "powershell"
    CMD = "cmd"


def detect_shell() -> Shell:
    """Detect current shell from environment."""
    # Unix-like systems
    if "SHELL" in os.environ:
        shell_path = os.environ["SHELL"]
        shell_name = Path(shell_path).name.lower()

        if "bash" in shell_name:
            return Shell.BASH
        elif "zsh" in shell_name:
            return Shell.ZSH
        elif "fish" in shell_name:
            return Shell.FISH

    # Windows
    if sys.platform == "win32":
        # Check if running in PowerShell
        if os.environ.get("PSModulePath"):
            return Shell.POWERSHELL
        # Otherwise assume cmd
        return Shell.CMD

    # Default to bash if unsure
    return Shell.BASH


def parse_shell(shell_name: str) -> Shell:
    """Parse shell name from string."""
    shell_name = shell_name.lower()
    try:
        return Shell(shell_name)
    except ValueError:
        raise ValueError(f"Unsupported shell: {shell_name}")


def get_activation_script(venv_path: Path, shell: Shell) -> str:
    """Get activation script path for shell."""
    if shell in (Shell.BASH, Shell.ZSH):
        return str(venv_path / "bin" / "activate")
    elif shell == Shell.FISH:
        return str(venv_path / "bin" / "activate.fish")
    elif shell == Shell.POWERSHELL:
        return str(venv_path / "Scripts" / "Activate.ps1")
    elif shell == Shell.CMD:
        return str(venv_path / "Scripts" / "activate.bat")
    else:
        raise ValueError(f"Unsupported shell: {shell}")


def format_export_commands(env_vars: dict[str, str], shell: Shell) -> list[str]:
    """Format export commands for shell."""
    commands = []

    if shell in (Shell.BASH, Shell.ZSH):
        # Bash/Zsh: export VAR="value"
        for key, value in env_vars.items():
            commands.append(f'export {key}="{value}"')

    elif shell == Shell.FISH:
        # Fish: set -x VAR "value"
        for key, value in env_vars.items():
            commands.append(f'set -x {key} "{value}"')

    elif shell == Shell.POWERSHELL:
        # PowerShell: Ensure HOME is set, then export variables
        commands.append('if (-not $env:HOME) { $env:HOME = $env:USERPROFILE }')
        for key, value in env_vars.items():
            commands.append(f'$env:{key}="{value}"')

    elif shell == Shell.CMD:
        # CMD: set VAR=value
        for key, value in env_vars.items():
            commands.append(f'set {key}={value}')

    return commands


def format_activation_command(script_path: str, shell: Shell) -> str:
    """Format activation command for shell."""
    if shell in (Shell.BASH, Shell.ZSH, Shell.FISH):
        return f'source {script_path}'
    elif shell == Shell.POWERSHELL:
        return f'& {script_path}'
    elif shell == Shell.CMD:
        return script_path
    else:
        raise ValueError(f"Unsupported shell: {shell}")
```

### 2. Activate Command

```python
# src/prime_uve/cli/activate.py
"""prime-uve activate command."""
import click
from pathlib import Path

from prime_uve.cli import output, errors
from prime_uve.core.paths import expand_path_variables
from prime_uve.core.project import find_project_root
from prime_uve.core.env_file import find_env_file, read_env_file, get_venv_path
from prime_uve.utils.shell import detect_shell, parse_shell, get_activation_script, format_export_commands, format_activation_command


@click.command()
@click.option("--shell", type=str, help="Override shell detection (bash, zsh, fish, powershell, cmd)")
@click.pass_context
def activate(ctx: click.Context, shell: str | None) -> None:
    """Output activation commands for current venv and export all .env.uve variables.

    Detects your shell and outputs appropriate commands to:
    1. Export ALL environment variables from .env.uve
    2. Activate the virtual environment

    Usage:
        eval "$(prime-uve activate)"           Auto-detect shell
        eval "$(prime-uve activate --shell bash)"  Force bash

    Supported shells: bash, zsh, fish, powershell, cmd

    Example .env.uve:
        UV_PROJECT_ENVIRONMENT=${HOME}/prime-uve/venvs/myapp_a1b2c3d4
        DATABASE_URL=postgresql://localhost/mydb
        DEBUG=true

    Result (bash):
        export UV_PROJECT_ENVIRONMENT="${HOME}/prime-uve/venvs/myapp_a1b2c3d4"
        export DATABASE_URL="postgresql://localhost/mydb"
        export DEBUG="true"
        source /home/user/prime-uve/venvs/myapp_a1b2c3d4/bin/activate
    """
    verbose = ctx.obj.get("verbose", False)

    try:
        # 1. Detect or parse shell
        if shell:
            try:
                shell_enum = parse_shell(shell)
            except ValueError as e:
                raise errors.UserError(
                    str(e),
                    hint="Supported shells: bash, zsh, fish, powershell, cmd"
                )
        else:
            shell_enum = detect_shell()

        output.verbose(f"Detected shell: {shell_enum.value}")

        # 2. Find project root
        project_root = find_project_root()
        if not project_root:
            raise errors.UserError(
                "Not in a Python project",
                hint="Navigate to a project directory with pyproject.toml"
            )

        output.verbose(f"Project root: {project_root}")

        # 3. Find and read .env.uve
        env_file = find_env_file(project_root)
        if not env_file.exists():
            raise errors.UserError(
                "No .env.uve file found",
                hint="Run 'prime-uve init' to initialize this project"
            )

        # Read ALL variables from .env.uve
        env_vars = read_env_file(env_file)
        output.verbose(f"Found {len(env_vars)} environment variable(s)")

        # 4. Get and expand venv path for activation
        venv_path_raw = get_venv_path(env_file, expand=False)
        if not venv_path_raw:
            raise errors.UserError(
                "No UV_PROJECT_ENVIRONMENT in .env.uve",
                hint="Run 'prime-uve init' to set up venv"
            )

        venv_path = expand_path_variables(venv_path_raw)
        output.verbose(f"Venv path: {venv_path}")

        # 5. Check venv exists
        if not venv_path.exists():
            raise errors.UserError(
                f"Venv does not exist: {venv_path}",
                hint="Run 'uv sync' to create the virtual environment"
            )

        # 6. Get activation script path
        activation_script = get_activation_script(venv_path, shell_enum)
        output.verbose(f"Activation script: {activation_script}")

        # 7. Generate output commands
        # First, export all environment variables
        export_commands = format_export_commands(env_vars, shell_enum)

        # Then, activation command
        activate_command = format_activation_command(activation_script, shell_enum)

        # 8. Output (to stdout, for eval)
        for cmd in export_commands:
            click.echo(cmd)
        click.echo(activate_command)

    except errors.CliError:
        raise
    except Exception as e:
        errors.handle_error(e, verbose)
```

### 3. Testing

```python
# tests/utils/test_shell.py
"""Test shell detection utilities."""
import pytest
from pathlib import Path

from prime_uve.utils.shell import Shell, detect_shell, parse_shell, get_activation_script, format_export_commands


def test_parse_shell():
    """Test shell name parsing."""
    assert parse_shell("bash") == Shell.BASH
    assert parse_shell("zsh") == Shell.ZSH
    assert parse_shell("fish") == Shell.FISH
    assert parse_shell("POWERSHELL") == Shell.POWERSHELL

    with pytest.raises(ValueError):
        parse_shell("invalid")


def test_get_activation_script():
    """Test activation script path generation."""
    venv = Path("/home/user/venv")

    assert "bin/activate" in get_activation_script(venv, Shell.BASH)
    assert "bin/activate" in get_activation_script(venv, Shell.ZSH)
    assert "bin/activate.fish" in get_activation_script(venv, Shell.FISH)
    assert "Scripts/Activate.ps1" in get_activation_script(venv, Shell.POWERSHELL)
    assert "Scripts/activate.bat" in get_activation_script(venv, Shell.CMD)


def test_format_export_commands_bash():
    """Test export command formatting for bash."""
    env_vars = {
        "UV_PROJECT_ENVIRONMENT": "${HOME}/venvs/test",
        "DEBUG": "true"
    }

    commands = format_export_commands(env_vars, Shell.BASH)
    assert len(commands) == 2
    assert 'export UV_PROJECT_ENVIRONMENT="${HOME}/venvs/test"' in commands
    assert 'export DEBUG="true"' in commands


def test_format_export_commands_fish():
    """Test export command formatting for fish."""
    env_vars = {"VAR": "value"}
    commands = format_export_commands(env_vars, Shell.FISH)
    assert 'set -x VAR "value"' in commands


def test_format_export_commands_powershell():
    """Test export command formatting for PowerShell."""
    env_vars = {"VAR": "value"}
    commands = format_export_commands(env_vars, Shell.POWERSHELL)
    # Should include HOME setting
    assert any("$env:HOME" in cmd for cmd in commands)
    assert '$env:VAR="value"' in commands


# tests/cli/test_activate.py
"""Test prime-uve activate command."""
def test_activate_basic(isolated_cli, tmp_path):
    """Test basic activation output."""
    # Setup project
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text('[project]\nname="test"')

    venv = tmp_path / "venvs" / "test"
    venv.mkdir(parents=True)
    (venv / "bin").mkdir()
    (venv / "bin" / "activate").touch()

    env_file = project / ".env.uve"
    env_file.write_text(f"UV_PROJECT_ENVIRONMENT={tmp_path}/venvs/test\nDEBUG=true")

    # Test
    result = isolated_cli.invoke(cli, ["activate", "--shell", "bash"])
    assert result.exit_code == 0
    assert "export UV_PROJECT_ENVIRONMENT=" in result.output
    assert "export DEBUG=" in result.output
    assert "source" in result.output
    assert "activate" in result.output


def test_activate_not_in_project(isolated_cli):
    """Test error when not in project."""
    result = isolated_cli.invoke(cli, ["activate"])
    assert result.exit_code == 1
    assert "Not in a Python project" in result.output


def test_activate_no_env_file(isolated_cli, tmp_path):
    """Test error when .env.uve missing."""
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").touch()

    result = isolated_cli.invoke(cli, ["activate"])
    assert result.exit_code == 1
    assert "No .env.uve file" in result.output


def test_activate_venv_not_exists(isolated_cli, tmp_path):
    """Test error when venv doesn't exist."""
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").touch()
    (project / ".env.uve").write_text("UV_PROJECT_ENVIRONMENT=/nonexistent/venv")

    result = isolated_cli.invoke(cli, ["activate"])
    assert result.exit_code == 1
    assert "does not exist" in result.output


def test_activate_multiple_env_vars(isolated_cli, tmp_path):
    """Test multiple environment variables exported."""
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text('[project]\nname="test"')

    venv = tmp_path / "venvs" / "test"
    venv.mkdir(parents=True)
    (venv / "bin").mkdir()
    (venv / "bin" / "activate").touch()

    env_file = project / ".env.uve"
    env_file.write_text(
        f"UV_PROJECT_ENVIRONMENT={tmp_path}/venvs/test\n"
        "DATABASE_URL=postgres://localhost/db\n"
        "SECRET_KEY=mysecret"
    )

    result = isolated_cli.invoke(cli, ["activate", "--shell", "bash"])
    assert result.exit_code == 0
    assert "export UV_PROJECT_ENVIRONMENT=" in result.output
    assert "export DATABASE_URL=" in result.output
    assert "export SECRET_KEY=" in result.output
```

## Acceptance Criteria

### Must Have

- ✅ Auto-detects shell from environment
- ✅ `--shell` override works
- ✅ Exports ALL variables from .env.uve (not just UV_PROJECT_ENVIRONMENT)
- ✅ Outputs correct export syntax for each shell
- ✅ Outputs correct activation command for each shell
- ✅ Expands `${HOME}` in venv path for activation
- ✅ Preserves variable format in export commands (doesn't expand)
- ✅ Works with `eval "$(prime-uve activate)"`
- ✅ Error if not in a project
- ✅ Error if .env.uve missing
- ✅ Error if venv doesn't exist
- ✅ Supports bash, zsh, fish, PowerShell, cmd

### Should Have

- ✅ Verbose mode shows detection details
- ✅ Clear error messages with hints
- ✅ Help text with examples
- ✅ On Windows PowerShell, ensures HOME is set

### Nice to Have

- Detect if already activated (skip redundant activation)
- Deactivation command helper
- Shell-specific instructions in error messages

## Example Usage

### Bash/Zsh
```bash
$ eval "$(prime-uve activate)"
# Exports all .env.uve variables and activates venv

$ prime-uve activate --shell bash
export UV_PROJECT_ENVIRONMENT="${HOME}/prime-uve/venvs/myapp_a1b2c3d4"
export DATABASE_URL="postgresql://localhost/mydb"
export DEBUG="true"
source /home/user/prime-uve/venvs/myapp_a1b2c3d4/bin/activate
```

### Fish
```fish
$ eval (prime-uve activate --shell fish)
set -x UV_PROJECT_ENVIRONMENT "${HOME}/prime-uve/venvs/myapp_a1b2c3d4"
set -x DATABASE_URL "postgresql://localhost/mydb"
set -x DEBUG "true"
source /home/user/prime-uve/venvs/myapp_a1b2c3d4/bin/activate.fish
```

### PowerShell
```powershell
PS> prime-uve activate --shell powershell | Invoke-Expression
$env:HOME = $env:USERPROFILE  # If not set
$env:UV_PROJECT_ENVIRONMENT="${HOME}/prime-uve/venvs/myapp_a1b2c3d4"
$env:DATABASE_URL="postgresql://localhost/mydb"
$env:DEBUG="true"
& C:\Users\user\prime-uve\venvs\myapp_a1b2c3d4\Scripts\Activate.ps1
```

## Success Metrics

- ✅ All unit tests pass (target: 12+ tests)
- ✅ 100% coverage of activate command and shell utils
- ✅ Works on all supported shells
- ✅ eval'd commands work correctly
- ✅ All .env.uve variables exported
- ✅ Clear error messages

## Future Enhancements

1. **Deactivate Helper**: `prime-uve deactivate` to reverse activation
2. **Shell Integration**: Add to .bashrc/.zshrc automatically
3. **Smart Detection**: Detect if already activated, skip if so
4. **Shell Completion**: Provide shell completion scripts
5. **Variable Expansion Options**: `--expand` to expand variables in exports

## References

- Architecture Design: `_todo/pending/architecture-design.md` (Section 6.4)
- Task 1.3: .env.uve File Management (reading variables)

## Notes

- This command outputs to stdout (for eval), errors to stderr
- Must preserve variable format (${HOME} not expanded in exports)
- But must expand for activation script path (venv must exist locally)
- Shell detection may not be perfect, --shell override is critical
- Consider adding shell-specific examples to help text
