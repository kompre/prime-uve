"""Dir command implementation for prime-uve."""

import subprocess
import sys


from prime_uve.cli.output import error, info
from prime_uve.core.paths import get_venv_base_dir


def dir_command(
    ctx, verbose: bool, yes: bool, dry_run: bool, json_output: bool
) -> None:
    """
    Open the venvs base directory in the system file explorer.

    Args:
        ctx: Click context
        verbose: Show verbose output
        yes: Skip confirmations (unused here)
        dry_run: Dry run mode - show path but don't open
        json_output: Output as JSON (unused here)
    """
    venv_base = get_venv_base_dir()

    if verbose or dry_run:
        info(f"Venvs base directory: {venv_base}")

    # Check if directory exists
    if not venv_base.exists():
        error(f"Venvs directory does not exist: {venv_base}")
        info("Run 'prime-uve init' in a project to create it.")
        sys.exit(1)

    # Dry run: just show path, don't open
    if dry_run:
        info("Dry run: skipping file explorer launch")
        return

    # Open in file explorer based on platform
    try:
        if sys.platform == "win32":
            # Windows: use explorer
            subprocess.run(["explorer", str(venv_base)], check=False)
        elif sys.platform == "darwin":
            # macOS: use open
            subprocess.run(["open", str(venv_base)], check=True)
        else:
            # Linux: try xdg-open
            subprocess.run(["xdg-open", str(venv_base)], check=True)

        if verbose:
            info(f"Opened {venv_base} in file explorer")

    except subprocess.CalledProcessError as e:
        error(f"Failed to open directory: {e}")
        sys.exit(1)
    except FileNotFoundError:
        error(f"File explorer command not found for platform: {sys.platform}")
        info(f"Please open manually: {venv_base}")
        sys.exit(1)
