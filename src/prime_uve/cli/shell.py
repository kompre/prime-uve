"""Shell command implementation for prime-uve."""

import os
import subprocess
import sys

import click

from prime_uve.cli.output import info
from prime_uve.core.env_file import EnvFileError, find_env_file_strict, read_env_file
from prime_uve.core.paths import expand_path_variables
from prime_uve.core.project import find_project_root
from prime_uve.utils.shell import detect_shell


def shell_command(
    ctx: click.Context,
    shell_override: str | None,
    verbose: bool,
    yes: bool,
    dry_run: bool,
    json_output: bool,
) -> None:
    """Spawn a new shell with venv activated and environment loaded.

    This command:
    - Reads all variables from .env.uve
    - Activates the project's venv
    - Spawns a new shell with the activated environment

    Args:
        ctx: Click context
        shell_override: Override shell detection
        verbose: Show detailed output
        yes: Not applicable for shell
        dry_run: Not applicable for shell
        json_output: Not applicable for shell

    Raises:
        click.ClickException: On errors
    """
    try:
        # 1. Find project root
        project_root = find_project_root()
        if not project_root:
            raise click.ClickException(
                "Not in a Python project\n"
                "Could not find pyproject.toml in current directory or any parent directory.\n\n"
                "Run 'prime-uve shell' from within a project directory."
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
                "Empty .env.uve file\nRun 'prime-uve init' to configure the project."
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

        # 4. Prepare environment
        new_env = os.environ.copy()

        # Set all variables from .env.uve
        # Only expand UV_PROJECT_ENVIRONMENT - other vars may contain URLs or other data
        for var_name, var_value in env_vars.items():
            if var_name == "UV_PROJECT_ENVIRONMENT":
                # Expand path variables for the venv path
                new_env[var_name] = str(expand_path_variables(var_value))
            else:
                # Keep other variables as-is (may contain URLs, etc.)
                new_env[var_name] = var_value

        # Set VIRTUAL_ENV
        new_env["VIRTUAL_ENV"] = str(venv_path_expanded)

        # Prepend venv's bin/Scripts to PATH
        if sys.platform == "win32":
            venv_bin = venv_path_expanded / "Scripts"
        else:
            venv_bin = venv_path_expanded / "bin"

        if not venv_bin.exists():
            raise click.ClickException(
                f"Venv binary directory not found: {venv_bin}\n"
                f"The venv may be corrupted. To recreate:\n"
                f"  prime-uve init --force"
            )

        # Prepend to PATH
        current_path = new_env.get("PATH", "")
        new_env["PATH"] = f"{venv_bin}{os.pathsep}{current_path}"

        # Ensure HOME is set on Windows
        if sys.platform == "win32" and "HOME" not in new_env:
            new_env["HOME"] = new_env.get("USERPROFILE", "")

        # Set prompt to show venv name
        venv_name = venv_path_expanded.name

        # Set PS1 for bash/zsh to include venv name
        # Keep existing PS1 if set, otherwise use a default
        if "PS1" in new_env:
            # Prepend venv name if not already present
            if venv_name not in new_env["PS1"]:
                new_env["PS1"] = f"({venv_name}) {new_env['PS1']}"
        else:
            # Set a default PS1 with venv name
            new_env["PS1"] = f"({venv_name}) \\u@\\h:\\w\\$ "

        # 5. Determine shell to spawn
        if shell_override:
            shell_cmd = shell_override
        else:
            # Detect current shell
            detected = detect_shell()
            # Map to executable name
            shell_map = {
                "bash": "bash",
                "zsh": "zsh",
                "fish": "fish",
                "pwsh": "pwsh",
                "cmd": "cmd",
            }
            shell_cmd = shell_map.get(detected, "bash")

        if verbose:
            info(f"Spawning new {shell_cmd} shell with activated venv")
            info(f"Virtual environment: {venv_path_expanded}")
            info(f"Environment variables loaded: {len(env_vars)}")
            info("Type 'exit' to return to the original shell")

        # 6. Spawn shell
        try:
            # Use interactive shell flags
            if shell_cmd in ("bash", "zsh"):
                subprocess.run([shell_cmd, "-i"], env=new_env)
            elif shell_cmd == "fish":
                subprocess.run([shell_cmd], env=new_env)
            elif shell_cmd == "pwsh":
                subprocess.run(["pwsh", "-NoLogo"], env=new_env)
            elif shell_cmd == "cmd":
                subprocess.run(["cmd"], env=new_env)
            else:
                # Fallback - try to run the shell directly
                subprocess.run([shell_cmd], env=new_env)

        except FileNotFoundError:
            raise click.ClickException(
                f"Shell not found: {shell_cmd}\n"
                f"Make sure {shell_cmd} is installed and in PATH.\n"
                f"You can specify a different shell with --shell option."
            )

    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Unexpected error: {e}")
