"""Shared venv discovery utilities.

This module provides functions for discovering and managing venv directories,
shared between list and prune commands.
"""

from pathlib import Path

from prime_uve.core.paths import expand_path_variables, get_venv_base_dir
from prime_uve.utils.disk import get_disk_usage


def scan_venv_directory() -> list[Path]:
    """
    Scan venv base directory for all venv directories.

    Returns:
        List of venv directory paths, or empty list if base doesn't exist
        or can't be accessed.

    Example:
        >>> venvs = scan_venv_directory()
        >>> print(f"Found {len(venvs)} venv(s)")
        Found 8 venv(s)
    """
    venv_base = get_venv_base_dir()
    if not venv_base.exists():
        return []

    try:
        return [d for d in venv_base.iterdir() if d.is_dir()]
    except (OSError, PermissionError):
        return []


def find_untracked_venvs(
    cache_entries: dict, calculate_disk_usage: bool = False
) -> list[dict]:
    """
    Find venvs on disk that aren't in cache (treat as orphans/untracked).

    Args:
        cache_entries: Dictionary of cache entries (project_path -> entry)
        calculate_disk_usage: If True, calculate disk usage (slower). Default False.

    Returns:
        List of untracked venv dictionaries with keys:
        - project_name: Extracted from directory name (e.g., "test-project_abc123" -> "test-project")
        - venv_path: None (no variable form for untracked)
        - venv_path_expanded: Path object to venv directory
        - hash: None (no hash for untracked)
        - created_at: None (no creation time for untracked)
        - is_valid: False (treat as orphan)
        - env_venv_path: None
        - disk_usage_bytes: Size in bytes (0 if calculate_disk_usage=False)

    Example:
        >>> from prime_uve.core.cache import Cache
        >>> cache = Cache()
        >>> mappings = cache.list_all()
        >>> untracked = find_untracked_venvs(mappings, calculate_disk_usage=True)
        >>> for venv in untracked:
        ...     print(f"{venv['project_name']}: {venv['disk_usage_bytes']:,} bytes")
    """
    all_venvs = scan_venv_directory()
    tracked_venvs = set()

    # Build set of tracked venv paths from cache
    for cache_entry in cache_entries.values():
        venv_path_expanded = expand_path_variables(cache_entry["venv_path"])
        tracked_venvs.add(venv_path_expanded)

    # Find untracked venvs
    untracked = []
    for venv_dir in all_venvs:
        if venv_dir not in tracked_venvs:
            # Extract project name from directory name
            # e.g., "test-project_abc123" -> "test-project"
            dir_name = venv_dir.name
            project_name = dir_name.rsplit("_", 1)[0] if "_" in dir_name else dir_name

            # Calculate disk usage only if requested
            disk_usage = 0
            if calculate_disk_usage:
                try:
                    disk_usage = get_disk_usage(venv_dir)
                except Exception:
                    pass

            untracked.append(
                {
                    "project_name": f"<unknown: {project_name}>",
                    "venv_path": None,  # No variable form for untracked
                    "venv_path_expanded": venv_dir,
                    "hash": None,  # No hash for untracked
                    "created_at": None,  # No creation time for untracked
                    "is_valid": False,  # Treat as orphan
                    "env_venv_path": None,
                    "disk_usage_bytes": disk_usage,
                }
            )

    return untracked
