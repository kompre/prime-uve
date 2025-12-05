"""Activate command implementation for prime-uve."""

import sys
from pathlib import Path

import click

from prime_uve.cli.output import echo, error
from prime_uve.core.env_file import EnvFileError, find_env_file_strict, read_env_file
from prime_uve.core.paths import expand_path_variables
from prime_uve.core.project import ProjectError, find_project_root, get_project_metadata
from prime_uve.utils.shell import (
    detect_shell,
    generate_activation_command,
    generate_export_command,
)


def activate_command(
    ctx: click.Context,
    shell_override: str | None,
    verbose: bool,
    yes: bool,
    dry_run: bool,
    json_output: bool,
) -> None:
    """Output activation command for current venv.

    This command generates shell-specific commands to:
    - Export all variables from .env.uve
    - Activate the project's venv

    Args:
        ctx: Click context
        shell_override: Override shell detection (bash, zsh, fish, pwsh, cmd)
        verbose: Show detailed output (to stderr)
        yes: Not applicable for activate
        dry_run: Not applicable for activate
        json_output: Not applicable for activate

    Raises:
        click.ClickException: On errors (not in project, no .env.uve, etc.)
    """
    try:
        # 1. Find project root
        project_root = find_project_root()
        if not project_root:
            raise click.ClickException(
                "Not in a Python project\n"
                "Could not find pyproject.toml in current directory or any parent directory.\n\n"
                "Run 'prime-uve activate' from within a project directory."
            )

        # 2. Find and read .env.uve
        try:
            env_file = find_env_file_strict(project_root)
        except EnvFileError:
            raise click.ClickException(
                "Project not initialized\n"
                "No .env.uve file found.\n\n"
                "Run 'prime-uve init' to initialize the project."
            )

        env_vars = read_env_file(env_file)
        if not env_vars:
            raise click.ClickException(
                "Empty .env.uve file\n" "Run 'prime-uve init' to configure the project."
            )

        # 3. Extract venv path and validate
        venv_path_var = env_vars.get("UV_PROJECT_ENVIRONMENT")
        if not venv_path_var:
            raise click.ClickException(
                ".env.uve missing UV_PROJECT_ENVIRONMENT\n"
                "Run 'prime-uve init --force' to reconfigure."
            )

        venv_path_expanded = expand_path_variables(venv_path_var)

        if not venv_path_expanded.exists():
            raise click.ClickException(
                f"Venv not found\n"
                f"Expected venv at: {venv_path_expanded}\n\n"
                f"The venv may have been deleted. To recreate:\n"
                f"  prime-uve init --force"
            )

        # 4. Detect or use shell override
        shell = shell_override or detect_shell()

        if verbose:
            try:
                metadata = get_project_metadata(project_root)
                project_name = metadata.name
            except ProjectError:
                project_name = "unknown"

            echo(f"[INFO] Detected shell: {shell}", err=True)
            echo(f"[INFO] Project: {project_name}", err=True)
            echo(f"[INFO] Venv: {venv_path_var}", err=True)
            echo(f"[INFO] Expanded: {venv_path_expanded}", err=True)
            echo(f"[INFO] Exporting {len(env_vars)} variables from .env.uve", err=True)

        # 5. Generate activation commands
        commands = []

        # On Windows PowerShell, ensure HOME is set first
        if shell in ("pwsh", "powershell") and sys.platform == "win32":
            commands.append("if (-not $env:HOME) { $env:HOME = $env:USERPROFILE }")

        # On Windows CMD, ensure HOME is set
        if shell == "cmd" and sys.platform == "win32":
            commands.append("if not defined HOME set HOME=%USERPROFILE%")

        # Export all variables from .env.uve
        for var_name, var_value in env_vars.items():
            export_cmd = generate_export_command(shell, var_name, var_value)
            commands.append(export_cmd)

        # Activation command
        activation_cmd = generate_activation_command(shell, venv_path_expanded)
        commands.append(activation_cmd)

        if verbose:
            activate_script_path = venv_path_expanded / (
                "Scripts/Activate.ps1"
                if shell in ("pwsh", "powershell")
                else "Scripts/activate.bat"
                if shell == "cmd"
                else "bin/activate.fish"
                if shell == "fish"
                else "bin/activate"
            )
            echo(f"[INFO] Activation script: {activate_script_path}", err=True)

        # 6. Output commands
        for cmd in commands:
            echo(cmd)

    except click.ClickException:
        # Re-raise Click exceptions as-is
        raise
    except Exception as e:
        # Wrap unexpected errors
        raise click.ClickException(f"Unexpected error: {e}")
