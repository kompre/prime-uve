"""uve wrapper implementation.

This module provides the main entry point for the uve command, which transparently
wraps uv commands with automatic .env.uve injection for external venv support.
"""

import os
import shutil
import subprocess
import sys

from prime_uve.core.env_file import find_env_file_strict


def is_uv_available() -> bool:
    """Check if uv command is available in PATH.

    Returns:
        True if uv is found, False otherwise
    """
    return shutil.which("uv") is not None


def main() -> None:
    """Main entry point for uve command.

    Wraps uv commands with automatic .env.uve injection for external venv support.
    Ensures HOME environment variable is set on Windows for cross-platform compatibility.

    Usage:
        uve add requests       → uv run --env-file .env.uve -- uv add requests
        uve sync               → uv run --env-file .env.uve -- uv sync
        uve run python app.py  → uv run --env-file .env.uve -- uv run python app.py

    Exit codes:
        0: Success
        1: Error (uv not found, env file issues, subprocess error)
        130: KeyboardInterrupt (Ctrl+C)
        Other: Forwarded from uv subprocess
    """
    # 1. Find .env.uve file (strict mode - don't create if missing)
    try:
        env_file = find_env_file_strict()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Ensure HOME is set on Windows for cross-platform compatibility
    env = os.environ.copy()
    if sys.platform == "win32" and "HOME" not in env:
        # Set HOME from USERPROFILE on Windows
        env["HOME"] = env.get("USERPROFILE", os.path.expanduser("~"))

    # 3. Build command: uv run --env-file .env.uve -- uv [args...]
    args = sys.argv[1:]  # All args after 'uve'
    # Convert to POSIX format and escape spaces for uv --env-file quirk
    env_file_str = env_file.as_posix().replace(" ", r"\ ")
    cmd = ["uv", "run", "--env-file", env_file_str, "--", "uv"] + args

    # 4. Check if uv is available
    if not is_uv_available():
        print(
            "Error: 'uv' command not found. Please install uv first.", file=sys.stderr
        )
        print("Visit: https://github.com/astral-sh/uv", file=sys.stderr)
        sys.exit(1)

    # 5. Run uv subprocess and forward exit code
    try:
        result = subprocess.run(cmd, env=env)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        # Standard exit code for SIGINT
        sys.exit(130)
    except Exception as e:
        print(f"Error running uv: {e}", file=sys.stderr)
        sys.exit(1)
