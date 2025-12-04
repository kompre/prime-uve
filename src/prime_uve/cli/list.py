"""List command implementation for prime-uve."""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import click

from prime_uve.cli.output import echo, error, info, print_json
from prime_uve.core.cache import Cache
from prime_uve.core.env_file import read_env_file
from prime_uve.core.paths import expand_path_variables, get_venv_base_dir


@dataclass
class ValidationResult:
    """Result of validating a cached project mapping."""

    project_name: str
    project_path: Path
    venv_path: str  # Variable form from cache (e.g., ${HOME}/...)
    venv_path_expanded: Path  # Expanded for local operations
    hash: str
    created_at: str
    is_valid: bool  # Simple: cache matches .env.uve or not
    env_venv_path: Optional[str]  # What's in .env.uve (for verbose display)
    disk_usage_bytes: int


def validate_project_mapping(project_path: str, cache_entry: dict) -> ValidationResult:
    """
    Validate a project mapping.

    Simplified validation: Does cached venv_path match UV_PROJECT_ENVIRONMENT in .env.uve?
    - Match → Valid
    - No match (any reason) → Orphan

    Args:
        project_path: Absolute path to project directory
        cache_entry: Cache entry with venv_path, project_name, etc.

    Returns:
        ValidationResult with validation status
    """
    project_path_obj = Path(project_path)
    venv_path = cache_entry["venv_path"]
    venv_path_expanded = expand_path_variables(venv_path)

    # Single check: does .env.uve match cache?
    env_venv_path = None
    is_valid = False

    env_file = project_path_obj / ".env.uve"
    try:
        if env_file.exists():
            env_vars = read_env_file(env_file)
            env_venv_path = env_vars.get("UV_PROJECT_ENVIRONMENT")
            is_valid = env_venv_path == venv_path
    except Exception:
        pass  # Any error → not valid

    # Get disk usage if venv exists
    disk_usage = 0
    if venv_path_expanded.exists():
        try:
            disk_usage = get_disk_usage(venv_path_expanded)
        except Exception:
            pass

    return ValidationResult(
        project_name=cache_entry["project_name"],
        project_path=project_path_obj,
        venv_path=venv_path,
        venv_path_expanded=venv_path_expanded,
        hash=cache_entry["path_hash"],
        created_at=cache_entry["created_at"],
        is_valid=is_valid,
        env_venv_path=env_venv_path,
        disk_usage_bytes=disk_usage,
    )


def scan_venv_directory() -> list[Path]:
    """
    Scan venv base directory for all venv directories.

    Returns:
        List of venv directory paths
    """
    venv_base = get_venv_base_dir()
    if not venv_base.exists():
        return []

    try:
        return [d for d in venv_base.iterdir() if d.is_dir()]
    except (OSError, PermissionError):
        return []


def find_untracked_venvs(cache_entries: dict) -> list[dict]:
    """
    Find venvs on disk that aren't in cache (treat as orphans).

    Args:
        cache_entries: Dictionary of cache entries (project_path -> entry)

    Returns:
        List of untracked venv dictionaries
    """
    all_venvs = scan_venv_directory()
    tracked_venvs = set()

    # Build set of tracked venv paths
    for cache_entry in cache_entries.values():
        venv_path_expanded = expand_path_variables(cache_entry["venv_path"])
        tracked_venvs.add(venv_path_expanded)

    # Find untracked venvs
    untracked = []
    for venv_dir in all_venvs:
        if venv_dir not in tracked_venvs:
            # Extract project name from directory name (e.g., "test-project_abc123" -> "test-project")
            dir_name = venv_dir.name
            project_name = dir_name.rsplit("_", 1)[0] if "_" in dir_name else dir_name

            untracked.append(
                {
                    "project_name": f"<unknown: {project_name}>",
                    "venv_path": None,  # No variable form for untracked
                    "venv_path_expanded": venv_dir,
                    "hash": None,  # No hash for untracked
                    "created_at": None,  # No creation time for untracked
                    "is_valid": False,  # Treat as orphan
                    "env_venv_path": None,
                    "disk_usage_bytes": get_disk_usage(venv_dir),
                }
            )

    return untracked


def get_disk_usage(path: Path) -> int:
    """
    Calculate total disk usage of a directory in bytes.

    Args:
        path: Directory path

    Returns:
        Total size in bytes
    """
    total = 0
    try:
        for item in path.rglob("*"):
            if item.is_file():
                try:
                    total += item.stat().st_size
                except (OSError, PermissionError):
                    pass
    except (OSError, PermissionError):
        pass
    return total


def format_bytes(size: int) -> str:
    """
    Format bytes to human-readable string.

    Args:
        size: Size in bytes

    Returns:
        Formatted string (e.g., "125 MB", "1.5 GB")
    """
    if size == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0

    size_float = float(size)
    while size_float >= 1024 and unit_index < len(units) - 1:
        size_float /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{int(size_float)} {units[unit_index]}"
    else:
        return f"{size_float:.1f} {units[unit_index]}"


def truncate_path(path: str, max_length: int) -> str:
    """
    Truncate path to fit max_length, keeping most relevant parts.

    Args:
        path: Path string
        max_length: Maximum length

    Returns:
        Truncated path
    """
    if len(path) <= max_length:
        return path

    # Try to keep the end (most specific part)
    return "..." + path[-(max_length - 3) :]


def output_table(results: list, stats: dict, verbose: bool) -> None:
    """
    Output results as a formatted table.

    Args:
        results: List of validation results (ValidationResult or untracked dicts)
        stats: Statistics dictionary
        verbose: Whether to show verbose output
    """
    echo("Managed Virtual Environments\n")

    if verbose:
        # Wide format with disk usage
        for result in results:
            # Handle both ValidationResult and untracked venv dicts
            is_valid = (
                result.is_valid if hasattr(result, "is_valid") else result["is_valid"]
            )
            project_name = (
                result.project_name
                if hasattr(result, "project_name")
                else result["project_name"]
            )
            disk_usage = (
                result.disk_usage_bytes
                if hasattr(result, "disk_usage_bytes")
                else result["disk_usage_bytes"]
            )
            venv_path_expanded = (
                result.venv_path_expanded
                if hasattr(result, "venv_path_expanded")
                else result["venv_path_expanded"]
            )
            hash_val = result.hash if hasattr(result, "hash") else result.get("hash")
            created_at = (
                result.created_at
                if hasattr(result, "created_at")
                else result.get("created_at")
            )
            venv_path = (
                result.venv_path
                if hasattr(result, "venv_path")
                else result.get("venv_path")
            )
            env_venv_path = (
                result.env_venv_path
                if hasattr(result, "env_venv_path")
                else result.get("env_venv_path")
            )
            project_path = (
                result.project_path
                if hasattr(result, "project_path")
                else result.get("project_path")
            )

            # Use ASCII-safe symbols for Windows compatibility
            status_symbol = "[OK]" if is_valid else "[!]"
            status_text = "Valid" if is_valid else "Orphan"
            size = format_bytes(disk_usage)
            status_display = f"{status_symbol} {status_text}"

            color = "green" if is_valid else "red"
            # Show project name, status, size on first line
            formatted_line = f"{project_name:<20} "
            echo(formatted_line, nl=False)
            click.secho(f"{status_display:<15}", fg=color, nl=False)
            echo(f" {size}")  # Size on same line

            # Extra details in verbose mode
            if project_path:
                echo(f"  Project: {project_path}")
            echo(f"  Venv:    {venv_path_expanded}")
            if hash_val:
                echo(f"  Hash:    {hash_val}")
            if created_at:
                echo(f"  Created: {created_at}")

            if not is_valid and venv_path:
                echo(f"  Cache:     {venv_path}")
                echo(f"  .env.uve:  {env_venv_path or 'Not found (or path mismatch)'}")
            echo("")
    else:
        # Compact format - venv path at end so it can be full-length/clickable
        header = f"{'PROJECT':<20} {'STATUS':<15} {'VENV PATH'}"
        echo(header)
        echo("-" * 80)  # Fixed width separator

        for result in results:
            # Handle both ValidationResult and untracked venv dicts
            is_valid = (
                result.is_valid if hasattr(result, "is_valid") else result["is_valid"]
            )
            project_name = (
                result.project_name
                if hasattr(result, "project_name")
                else result["project_name"]
            )
            venv_path_expanded = (
                result.venv_path_expanded
                if hasattr(result, "venv_path_expanded")
                else result["venv_path_expanded"]
            )

            # Use ASCII-safe symbols for Windows compatibility
            status_symbol = "[OK]" if is_valid else "[!]"
            status_text = "Valid" if is_valid else "Orphan"
            status_display = f"{status_symbol} {status_text}"

            color = "green" if is_valid else "red"
            # Don't truncate venv path - show full path so user can click it
            formatted_line = f"{project_name:<20} "
            echo(formatted_line, nl=False)
            click.secho(f"{status_display:<15}", fg=color, nl=False)
            echo(f" {venv_path_expanded}")

    # Summary
    echo(
        f"\nSummary: {stats['total']} total, {stats['valid']} valid, {stats['orphaned']} orphaned"
    )

    if verbose and stats["total_disk_usage"] > 0:
        total_size = format_bytes(stats["total_disk_usage"])
        echo(f"Total disk usage: {total_size}")


def output_json_format(results: list, stats: dict) -> None:
    """
    Output results as JSON.

    Args:
        results: List of validation results (ValidationResult or untracked dicts)
        stats: Statistics dictionary
    """
    venvs_data = []
    for r in results:
        # Handle both ValidationResult and untracked venv dicts
        if hasattr(r, "is_valid"):
            # ValidationResult object
            venvs_data.append(
                {
                    "project_name": r.project_name,
                    "project_path": str(r.project_path),
                    "venv_path": r.venv_path,
                    "venv_path_expanded": str(r.venv_path_expanded),
                    "hash": r.hash,
                    "created_at": r.created_at,
                    "status": "valid" if r.is_valid else "orphan",
                    "cache_matches_env": r.is_valid,
                    "disk_usage_bytes": r.disk_usage_bytes,
                }
            )
        else:
            # Untracked venv dict
            venvs_data.append(
                {
                    "project_name": r["project_name"],
                    "project_path": None,  # Untracked venvs have no associated project
                    "venv_path": None,  # No cache entry
                    "venv_path_expanded": str(r["venv_path_expanded"]),
                    "hash": None,
                    "created_at": None,
                    "status": "orphan",
                    "cache_matches_env": False,
                    "disk_usage_bytes": r["disk_usage_bytes"],
                }
            )

    data = {
        "venvs": venvs_data,
        "summary": {
            "total": stats["total"],
            "valid": stats["valid"],
            "orphaned": stats["orphaned"],
            "total_disk_usage_bytes": stats["total_disk_usage"],
        },
    }
    print_json(data)


def list_command(
    ctx,
    orphan_only: bool,
    verbose: bool,
    yes: bool,
    dry_run: bool,
    json_output: bool,
) -> None:
    """
    List all managed venvs with validation status, including untracked venvs as orphans.

    Args:
        ctx: Click context
        orphan_only: Show only orphaned venvs
        verbose: Show verbose output
        yes: Skip confirmations (unused here)
        dry_run: Dry run mode (unused here)
        json_output: Output as JSON
    """
    # 1. Load cache
    try:
        cache = Cache()
        mappings = cache.list_all()
    except Exception as e:
        error(f"Failed to load cache: {e}")
        sys.exit(1)

    # 2. Validate all cached mappings
    results = []
    for project_path, cache_entry in mappings.items():
        result = validate_project_mapping(project_path, cache_entry)
        results.append(result)

    # 3. Find and add untracked venvs as orphans
    untracked_venvs = find_untracked_venvs(mappings)
    results.extend(untracked_venvs)

    # If no venvs at all (cached or untracked)
    if not results:
        if json_output:
            print_json(
                {
                    "venvs": [],
                    "summary": {
                        "total": 0,
                        "valid": 0,
                        "orphaned": 0,
                        "total_disk_usage_bytes": 0,
                    },
                }
            )
        else:
            info("No managed virtual environments found.")
            echo("\nRun 'prime-uve init' in a project directory to get started.")
        return

    # 4. Filter if requested
    if orphan_only:
        results = [
            r
            for r in results
            if not (r.is_valid if hasattr(r, "is_valid") else r["is_valid"])
        ]

        if not results:
            if json_output:
                print_json(
                    {
                        "venvs": [],
                        "summary": {
                            "total": 0,
                            "valid": 0,
                            "orphaned": 0,
                            "total_disk_usage_bytes": 0,
                        },
                    }
                )
            else:
                info("No orphaned venvs found. All cached venvs are valid!")
            return

    # 5. Calculate statistics
    total_cached = len(mappings)
    total_untracked = len(untracked_venvs)
    total_count = total_cached + total_untracked

    valid_count = sum(
        1 for r in results if (r.is_valid if hasattr(r, "is_valid") else r["is_valid"])
    )
    orphaned_count = sum(
        1
        for r in results
        if not (r.is_valid if hasattr(r, "is_valid") else r["is_valid"])
    )
    total_disk = sum(
        (
            r.disk_usage_bytes
            if hasattr(r, "disk_usage_bytes")
            else r["disk_usage_bytes"]
        )
        for r in results
    )

    stats = {
        "total": total_count,
        "valid": valid_count,
        "orphaned": orphaned_count,
        "total_disk_usage": total_disk,
    }

    # 6. Output
    if json_output:
        output_json_format(results, stats)
    else:
        output_table(results, stats, verbose)

        # Helpful tip for orphans
        if stats["orphaned"] > 0:
            echo(
                f"\nFound {stats['orphaned']} orphaned venv(s). "
                f"Run 'prime-uve prune --orphan' to clean up."
            )
