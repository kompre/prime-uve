"""Path generation and hashing utilities for prime-uve.

This module provides cross-platform path generation using platform-appropriate
cache and data directories, with ${PRIMEUVE_VENVS_PATH} variable for venv paths,
ensuring compatibility across Windows, macOS, and Linux.
"""

import hashlib
import os
import platform
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


def get_default_venvs_cache_path() -> Path:
    """Get platform-appropriate default venvs cache location.

    Returns platform-specific cache directories following OS conventions:
    - Linux: $XDG_CACHE_HOME/prime-uve/venvs or ~/.cache/prime-uve/venvs
    - macOS: ~/Library/Caches/prime-uve/venvs
    - Windows: %LOCALAPPDATA%/prime-uve/Cache/venvs

    Returns:
        Path to platform-appropriate venv cache directory
    """
    system = platform.system()

    if system == "Linux":
        xdg_cache = os.environ.get("XDG_CACHE_HOME")
        if xdg_cache:
            return Path(xdg_cache) / "prime-uve" / "venvs"
        return Path.home() / ".cache" / "prime-uve" / "venvs"

    elif system == "Darwin":  # macOS
        return Path.home() / "Library" / "Caches" / "prime-uve" / "venvs"

    elif system == "Windows":
        localappdata = os.environ.get("LOCALAPPDATA")
        if localappdata:
            return Path(localappdata) / "prime-uve" / "Cache" / "venvs"
        return Path.home() / "AppData" / "Local" / "prime-uve" / "Cache" / "venvs"

    else:
        # Fallback for unknown platforms
        return Path.home() / ".prime-uve" / "venvs"


def get_venvs_cache_path() -> Path:
    """Get venvs cache path respecting configuration hierarchy.

    Priority order:
    1. PRIMEUVE_VENVS_PATH environment variable (explicit override)
    2. Platform default (from get_default_venvs_cache_path)

    Returns:
        Path to venv cache directory
    """
    # 1. Check env variable
    env_path = os.environ.get("PRIMEUVE_VENVS_PATH")
    if env_path:
        return Path(env_path).expanduser().resolve()

    # 2. Use platform default
    return get_default_venvs_cache_path()


def get_default_data_path() -> Path:
    """Get platform-appropriate default data directory location.

    Returns platform-specific data directories following OS conventions:
    - Linux: $XDG_DATA_HOME/prime-uve or ~/.local/share/prime-uve
    - macOS: ~/Library/Application Support/prime-uve
    - Windows: %LOCALAPPDATA%/prime-uve/Data

    Returns:
        Path to platform-appropriate data directory
    """
    system = platform.system()

    if system == "Linux":
        xdg_data = os.environ.get("XDG_DATA_HOME")
        if xdg_data:
            return Path(xdg_data) / "prime-uve"
        return Path.home() / ".local" / "share" / "prime-uve"

    elif system == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "prime-uve"

    elif system == "Windows":
        localappdata = os.environ.get("LOCALAPPDATA")
        if localappdata:
            return Path(localappdata) / "prime-uve" / "Data"
        return Path.home() / "AppData" / "Local" / "prime-uve" / "Data"

    else:
        # Fallback for unknown platforms
        return Path.home() / ".prime-uve"


def get_data_path() -> Path:
    """Get data path with optional override support.

    Currently returns platform default. Could add PRIMEUVE_DATA_PATH
    environment variable override in the future if needed.

    Returns:
        Path to data directory
    """
    return get_default_data_path()


def generate_venv_path(project_path: Path) -> str:
    """Generate a venv path with ${PRIMEUVE_VENVS_PATH} variable.

    Creates a path string using ${PRIMEUVE_VENVS_PATH} variable (not expanded)
    so the same .env.uve file works across different users and platforms.
    The uve wrapper injects this variable at runtime based on platform defaults.

    The path format is: ${PRIMEUVE_VENVS_PATH}/{project_name}_{hash}

    Args:
        project_path: Absolute path to the project directory

    Returns:
        Path string with literal ${PRIMEUVE_VENVS_PATH} variable (not expanded)

    Example:
        >>> generate_venv_path(Path("/mnt/share/my-project"))
        '${PRIMEUVE_VENVS_PATH}/my-project_a1b2c3d4'
    """
    project_name = get_project_name(project_path)
    path_hash = generate_hash(project_path)

    # Use ${PRIMEUVE_VENVS_PATH} for platform-appropriate caching
    return f"${{PRIMEUVE_VENVS_PATH}}/{project_name}_{path_hash}"


def expand_path_variables(path: str) -> Path:
    """Expand ${HOME} and ${PRIMEUVE_VENVS_PATH} variables to actual paths.

    Converts a path string with variables to an actual pathlib.Path
    with the variables expanded. Used for local operations like checking if
    a venv exists.

    Supported variables:
    - ${HOME}: User home directory (Windows: USERPROFILE, Unix: HOME)
    - ${PRIMEUVE_VENVS_PATH}: Venv cache directory (from env or platform default)

    Args:
        path: Path string containing variables

    Returns:
        pathlib.Path with variables expanded to actual directories

    Example:
        >>> expand_path_variables("${HOME}/.prime-uve/venvs/myproject")
        Path('/home/user/.prime-uve/venvs/myproject')  # On Linux
        >>> expand_path_variables("${PRIMEUVE_VENVS_PATH}/myproject_abc123")
        Path('/home/user/.cache/prime-uve/venvs/myproject_abc123')  # On Linux
    """
    expanded = path

    # Replace ${PRIMEUVE_VENVS_PATH} if present
    if "${PRIMEUVE_VENVS_PATH}" in expanded:
        venvs_path = str(get_venvs_cache_path())
        expanded = expanded.replace("${PRIMEUVE_VENVS_PATH}", venvs_path)

    # Replace ${HOME} if present
    if "${HOME}" in expanded:
        # Determine home directory based on platform
        if sys.platform == "win32":
            home = (
                os.environ.get("HOME")
                or os.environ.get("USERPROFILE")
                or os.path.expanduser("~")
            )
        else:
            home = os.environ.get("HOME") or os.path.expanduser("~")
        expanded = expanded.replace("${HOME}", home)

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

    Returns the platform-appropriate venv cache directory, respecting
    PRIMEUVE_VENVS_PATH environment variable if set.

    Returns:
        Path to venv base directory

    Example:
        >>> get_venv_base_dir()
        Path('/home/user/.cache/prime-uve/venvs')  # On Linux (default)
        Path('/custom/venvs')  # If PRIMEUVE_VENVS_PATH=/custom/venvs
    """
    return get_venvs_cache_path()
