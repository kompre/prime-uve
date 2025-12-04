"""Path generation and hashing utilities for prime-uve.

This module provides cross-platform path generation using ${HOME} variable
for venv paths, ensuring compatibility across Windows, macOS, and Linux.
"""

import hashlib
import os
import sys
import tomllib
from pathlib import Path


def generate_hash(project_path: Path) -> str:
    """Generate a deterministic 8-character hash from a project path.

    Uses SHA256 and normalizes the path to ensure cross-platform consistency.
    The same project path will always generate the same hash regardless of
    platform or path separator style.

    Args:
        project_path: Absolute path to the project directory

    Returns:
        First 8 characters of the SHA256 hash as hexadecimal string

    Example:
        >>> generate_hash(Path("/mnt/share/my-project"))
        'a1b2c3d4'
    """
    # Resolve symlinks and normalize to POSIX style for cross-platform consistency
    normalized = project_path.resolve().as_posix()
    hash_obj = hashlib.sha256(normalized.encode())
    return hash_obj.hexdigest()[:8]


def get_project_name(project_path: Path) -> str:
    """Extract and sanitize project name from pyproject.toml or directory name.

    Tries to read project name from pyproject.toml first. If that fails or
    doesn't exist, uses the directory name. Sanitizes the result to be
    filesystem-safe.

    Args:
        project_path: Absolute path to the project directory

    Returns:
        Sanitized project name (lowercase, hyphens instead of special chars)

    Example:
        >>> get_project_name(Path("/home/user/My Project!"))
        'my-project'
    """
    name = None

    # Try to get name from pyproject.toml
    pyproject_path = project_path / "pyproject.toml"
    if pyproject_path.exists():
        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                name = data.get("project", {}).get("name")
        except (tomllib.TOMLDecodeError, KeyError, OSError):
            # Fall through to use directory name
            pass

    # Fall back to directory name
    if not name:
        name = project_path.name

    # Sanitize: lowercase, replace non-alphanumeric with hyphens
    sanitized = ""
    for char in name.lower():
        if char.isalnum():
            sanitized += char
        elif sanitized and sanitized[-1] != "-":
            # Add hyphen, but avoid consecutive hyphens
            sanitized += "-"

    # Remove trailing hyphens and handle empty result
    sanitized = sanitized.rstrip("-")
    return sanitized if sanitized else "project"


def generate_venv_path(project_path: Path) -> str:
    """Generate a venv path with ${HOME} variable for cross-platform compatibility.

    Creates a path string using ${HOME} variable (not expanded) so the same
    .env.uve file works across different users and platforms. The path format
    is: ${HOME}/prime-uve/venvs/{project_name}_{hash}

    Args:
        project_path: Absolute path to the project directory

    Returns:
        Path string with literal ${HOME} variable (not expanded)

    Example:
        >>> generate_venv_path(Path("/mnt/share/my-project"))
        '${HOME}/prime-uve/venvs/my-project_a1b2c3d4'
    """
    project_name = get_project_name(project_path)
    path_hash = generate_hash(project_path)

    # Always use ${HOME} for cross-platform compatibility
    return f"${{HOME}}/prime-uve/venvs/{project_name}_{path_hash}"


def expand_path_variables(path: str) -> Path:
    """Expand ${HOME} variable to actual home directory path.

    Converts a path string with ${HOME} variable to an actual pathlib.Path
    with the variable expanded. Used for local operations like checking if
    a venv exists.

    On Windows, uses USERPROFILE environment variable.
    On Unix/macOS, uses HOME environment variable.
    Falls back to os.path.expanduser('~') if variables not set.

    Args:
        path: Path string containing ${HOME} variable

    Returns:
        pathlib.Path with ${HOME} expanded to actual directory

    Example:
        >>> expand_path_variables("${HOME}/prime-uve/venvs/myproject")
        Path('/home/user/prime-uve/venvs/myproject')  # On Linux
        Path('C:/Users/user/prime-uve/venvs/myproject')  # On Windows
    """
    # Determine home directory based on platform
    if sys.platform == "win32":
        home = (
            os.environ.get("HOME")
            or os.environ.get("USERPROFILE")
            or os.path.expanduser("~")
        )
    else:
        home = os.environ.get("HOME") or os.path.expanduser("~")

    # Replace ${HOME} with actual home directory
    expanded = path.replace("${HOME}", home)
    return Path(expanded)


def ensure_home_set() -> None:
    """Ensure HOME environment variable is set (Windows compatibility).

    On Windows, HOME may not be set by default. This function ensures it's
    available by setting it to USERPROFILE if missing. This allows ${HOME}
    to work consistently across all platforms.

    Should be called before operations that rely on HOME variable being set.
    """
    if sys.platform == "win32" and "HOME" not in os.environ:
        userprofile = os.environ.get("USERPROFILE")
        if userprofile:
            os.environ["HOME"] = userprofile
        else:
            # Last resort fallback
            os.environ["HOME"] = os.path.expanduser("~")


def get_venv_base_dir() -> Path:
    """Get the base directory where all venvs are stored.

    Returns the expanded path to the venv base directory:
    ${HOME}/prime-uve/venvs -> /home/user/prime-uve/venvs

    Returns:
        Path to venv base directory
    """
    return expand_path_variables("${HOME}/prime-uve/venvs")
