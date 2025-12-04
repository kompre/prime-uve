"""Prune command implementation for prime-uve."""

import shutil
import sys
from pathlib import Path
from typing import Optional

import click

from prime_uve.cli.output import echo, error, info, success, warning, print_json
from prime_uve.core.cache import Cache
from prime_uve.core.env_file import find_env_file, read_env_file, write_env_file
from prime_uve.core.paths import expand_path_variables, get_venv_base_dir
from prime_uve.core.project import find_project_root


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
                    "size": get_disk_usage(venv_dir),
                }
            )

    return untracked


def is_orphaned(project_path: str, cache_entry: dict) -> bool:
    """
    Check if a cached venv is orphaned.

    Simplified validation: Does cached venv_path match UV_PROJECT_ENVIRONMENT in .env.uve?
    - Match → Not orphaned
    - No match (any reason) → Orphaned

    Args:
        project_path: Absolute path to project directory
        cache_entry: Cache entry with venv_path

    Returns:
        True if orphaned, False otherwise
    """
    project_path_obj = Path(project_path)
    cached_venv_path = cache_entry["venv_path"]

    env_file = project_path_obj / ".env.uve"
    try:
        if env_file.exists():
            env_vars = read_env_file(env_file)
            env_venv_path = env_vars.get("UV_PROJECT_ENVIRONMENT")
            return env_venv_path != cached_venv_path
    except Exception:
        pass

    # If we can't read the file or it doesn't exist, it's orphaned
    return True


def remove_venv_directory(venv_path: str, dry_run: bool) -> tuple[bool, Optional[str]]:
    """
    Remove a venv directory.

    Args:
        venv_path: Venv path (may contain variables like ${HOME} or be a direct path)
        dry_run: If True, don't actually delete

    Returns:
        Tuple of (success, error_message)
    """
    try:
        # If path contains ${HOME}, expand it; otherwise treat as literal path
        if "${HOME}" in str(venv_path):
            venv_path_expanded = expand_path_variables(venv_path)
        else:
            venv_path_expanded = Path(venv_path)

        if not venv_path_expanded.exists():
            return True, None  # Already gone

        if dry_run:
            return True, None

        shutil.rmtree(venv_path_expanded)
        return True, None

    except Exception as e:
        return False, str(e)


def prune_all(
    ctx,
    verbose: bool,
    yes: bool,
    dry_run: bool,
    json_output: bool,
) -> None:
    """
    Remove all venv directories and clear cache.

    Args:
        ctx: Click context
        verbose: Show verbose output
        yes: Skip confirmation
        dry_run: Dry run mode
        json_output: Output as JSON
    """
    # Load cache
    try:
        cache = Cache()
        mappings = cache.list_all()
    except Exception as e:
        error(f"Failed to load cache: {e}")
        sys.exit(1)

    if not mappings:
        if json_output:
            print_json({"removed": [], "failed": [], "total_size_freed": 0})
        else:
            info("No managed venvs found.")
        return

    # Calculate total size
    total_size = 0
    venvs_to_remove = []

    for project_path, cache_entry in mappings.items():
        venv_path = cache_entry["venv_path"]
        venv_path_expanded = expand_path_variables(venv_path)
        size = 0
        if venv_path_expanded.exists():
            size = get_disk_usage(venv_path_expanded)
        total_size += size
        venvs_to_remove.append(
            {
                "project_name": cache_entry["project_name"],
                "project_path": project_path,
                "venv_path": venv_path,
                "venv_path_expanded": str(venv_path_expanded),
                "size": size,
            }
        )

    # Show what will be removed
    if not json_output:
        warning(f"This will remove ALL {len(venvs_to_remove)} managed venv(s)!")
        echo("")
        for item in venvs_to_remove:
            echo(f"  - {item['project_name']} ({format_bytes(item['size'])})")
        echo("")
        echo(f"Total disk space to be freed: {format_bytes(total_size)}")
        echo("")

    # Confirm unless --yes
    if not yes and not dry_run:
        if not click.confirm("Are you sure you want to continue?"):
            info("Aborted.")
            return

    if dry_run and not json_output:
        info("[DRY RUN] No changes will be made.")
        echo("")

    # Remove venvs
    removed = []
    failed = []

    for item in venvs_to_remove:
        success_flag, error_msg = remove_venv_directory(item["venv_path"], dry_run)

        if success_flag:
            removed.append(item)
            if verbose and not json_output:
                echo(f"  Removed: {item['venv_path_expanded']}")
        else:
            failed.append({"venv": item, "error": error_msg})
            if not json_output:
                error(f"  Failed to remove {item['venv_path_expanded']}: {error_msg}")

    # Clear cache
    if not dry_run:
        try:
            cache.clear()
        except Exception as e:
            error(f"Failed to clear cache: {e}")
            sys.exit(1)

    # Output results
    if json_output:
        print_json(
            {
                "removed": [
                    {
                        "project_name": item["project_name"],
                        "project_path": item["project_path"],
                        "venv_path": item["venv_path"],
                        "size_bytes": item["size"],
                    }
                    for item in removed
                ],
                "failed": [
                    {
                        "project_name": item["venv"]["project_name"],
                        "project_path": item["venv"]["project_path"],
                        "venv_path": item["venv"]["venv_path"],
                        "error": item["error"],
                    }
                    for item in failed
                ],
                "total_size_freed": sum(item["size"] for item in removed),
            }
        )
    else:
        echo("")
        if dry_run:
            info(
                f"[DRY RUN] Would remove {len(removed)} venv(s) "
                f"and free {format_bytes(total_size)}"
            )
        else:
            success(
                f"Removed {len(removed)} venv(s) and freed {format_bytes(total_size)}"
            )
            if failed:
                warning(f"Failed to remove {len(failed)} venv(s)")


def prune_orphan(
    ctx,
    verbose: bool,
    yes: bool,
    dry_run: bool,
    json_output: bool,
) -> None:
    """
    Remove only orphaned venv directories, including untracked venvs.

    Args:
        ctx: Click context
        verbose: Show verbose output
        yes: Skip confirmation
        dry_run: Dry run mode
        json_output: Output as JSON
    """
    # Load cache
    try:
        cache = Cache()
        mappings = cache.list_all()
    except Exception as e:
        error(f"Failed to load cache: {e}")
        sys.exit(1)

    # Find cached orphaned venvs
    orphaned_venvs = []
    total_size = 0

    for project_path, cache_entry in mappings.items():
        if is_orphaned(project_path, cache_entry):
            venv_path = cache_entry["venv_path"]
            venv_path_expanded = expand_path_variables(venv_path)
            size = 0
            if venv_path_expanded.exists():
                size = get_disk_usage(venv_path_expanded)
            total_size += size
            orphaned_venvs.append(
                {
                    "project_name": cache_entry["project_name"],
                    "project_path": project_path,
                    "venv_path": venv_path,
                    "venv_path_expanded": str(venv_path_expanded),
                    "size": size,
                    "is_tracked": True,  # Mark as from cache
                }
            )

    # Find untracked venvs (also treat as orphans)
    untracked_venvs = find_untracked_venvs(mappings)
    for untracked in untracked_venvs:
        total_size += untracked["size"]
        orphaned_venvs.append(
            {
                "project_name": untracked["project_name"],
                "project_path": None,  # No associated project
                "venv_path": None,  # No cache entry
                "venv_path_expanded": str(untracked["venv_path_expanded"]),
                "size": untracked["size"],
                "is_tracked": False,  # Mark as untracked
            }
        )

    if not orphaned_venvs:
        if json_output:
            print_json({"removed": [], "failed": [], "total_size_freed": 0})
        else:
            info("No orphaned venvs found. All cached venvs are valid!")
        return

    # Show what will be removed
    if not json_output:
        echo(f"Found {len(orphaned_venvs)} orphaned venv(s) to remove:")
        echo("")
        for item in orphaned_venvs:
            echo(f"  - {item['project_name']} ({format_bytes(item['size'])})")
        echo("")
        echo(f"Total disk space to be freed: {format_bytes(total_size)}")
        echo("")

    # Confirm unless --yes
    if not yes and not dry_run:
        if not click.confirm("Continue?"):
            info("Aborted.")
            return

    if dry_run and not json_output:
        info("[DRY RUN] No changes will be made.")
        echo("")

    # Remove orphaned venvs
    removed = []
    failed = []

    for item in orphaned_venvs:
        venv_path_to_remove = item.get("venv_path") if item["is_tracked"] else None
        if not venv_path_to_remove:
            # For untracked venvs, construct the path directly
            venv_path_to_remove = item["venv_path_expanded"]

        success_flag, error_msg = remove_venv_directory(venv_path_to_remove, dry_run)

        if success_flag:
            removed.append(item)
            if not dry_run and item["is_tracked"]:
                # Remove from cache only for tracked venvs
                try:
                    cache.remove_mapping(Path(item["project_path"]))
                except Exception as e:
                    if not json_output:
                        warning(f"  Failed to remove from cache: {e}")

            if verbose and not json_output:
                echo(f"  Removed: {item['venv_path_expanded']}")
        else:
            failed.append({"venv": item, "error": error_msg})
            if not json_output:
                error(f"  Failed to remove {item['venv_path_expanded']}: {error_msg}")

    # Output results
    if json_output:
        print_json(
            {
                "removed": [
                    {
                        "project_name": item["project_name"],
                        "project_path": item.get("project_path"),
                        "venv_path": item.get("venv_path"),
                        "size_bytes": item["size"],
                    }
                    for item in removed
                ],
                "failed": [
                    {
                        "project_name": item["venv"]["project_name"],
                        "project_path": item["venv"].get("project_path"),
                        "venv_path": item["venv"].get("venv_path"),
                        "error": item["error"],
                    }
                    for item in failed
                ],
                "total_size_freed": sum(item["size"] for item in removed),
            }
        )
    else:
        echo("")
        if dry_run:
            info(
                f"[DRY RUN] Would remove {len(removed)} orphaned venv(s) "
                f"and free {format_bytes(total_size)}"
            )
        else:
            success(
                f"Removed {len(removed)} orphaned venv(s) "
                f"and freed {format_bytes(total_size)}"
            )
            if failed:
                warning(f"Failed to remove {len(failed)} venv(s)")


def prune_current(
    ctx,
    verbose: bool,
    yes: bool,
    dry_run: bool,
    json_output: bool,
) -> None:
    """
    Remove venv for current project.

    Args:
        ctx: Click context
        verbose: Show verbose output
        yes: Skip confirmation
        dry_run: Dry run mode
        json_output: Output as JSON
    """
    # Find project root
    try:
        project_root = find_project_root()
        if not project_root:
            error("Not in a Python project (no pyproject.toml found)")
            sys.exit(1)
    except Exception as e:
        error(f"Failed to find project root: {e}")
        sys.exit(1)

    # Load cache
    try:
        cache = Cache()
        cache_entry = cache.get_mapping(project_root)
    except Exception as e:
        error(f"Failed to load cache: {e}")
        sys.exit(1)

    if not cache_entry:
        if json_output:
            print_json({"removed": False, "error": "Project not found in cache"})
        else:
            error("Current project is not managed by prime-uve")
            info("Run 'prime-uve init' first to initialize this project")
        sys.exit(1)

    # Get venv info
    venv_path = cache_entry["venv_path"]
    venv_path_expanded = expand_path_variables(venv_path)
    project_name = cache_entry["project_name"]

    size = 0
    if venv_path_expanded.exists():
        size = get_disk_usage(venv_path_expanded)

    # Show what will be removed
    if not json_output:
        echo(f"Current project: {project_name}")
        echo(f"Venv path: {venv_path_expanded}")
        if size > 0:
            echo(f"Size: {format_bytes(size)}")
        echo("")

    # Confirm unless --yes
    if not yes and not dry_run:
        if not click.confirm(f"Remove venv for '{project_name}' and clear .env.uve?"):
            info("Aborted.")
            return

    if dry_run and not json_output:
        info("[DRY RUN] No changes will be made.")
        echo("")

    # Remove venv
    success_flag, error_msg = remove_venv_directory(venv_path, dry_run)

    if not success_flag:
        if json_output:
            print_json({"removed": False, "error": error_msg})
        else:
            error(f"Failed to remove venv: {error_msg}")
        sys.exit(1)

    # Remove from cache
    if not dry_run:
        try:
            cache.remove_mapping(project_root)
        except Exception as e:
            if json_output:
                print_json({"removed": False, "error": f"Failed to update cache: {e}"})
            else:
                error(f"Failed to remove from cache: {e}")
            sys.exit(1)

        # Clear .env.uve
        try:
            env_file = find_env_file()
            if env_file and env_file.exists():
                write_env_file(env_file, {})
        except Exception as e:
            if not json_output:
                warning(f"Failed to clear .env.uve: {e}")

    # Output results
    if json_output:
        print_json(
            {
                "removed": True,
                "project_name": project_name,
                "venv_path": venv_path,
                "size_bytes": size,
            }
        )
    else:
        echo("")
        if dry_run:
            info(
                f"[DRY RUN] Would remove venv for '{project_name}' "
                f"and free {format_bytes(size)}"
            )
        else:
            success(f"Removed venv for '{project_name}' and freed {format_bytes(size)}")


def prune_path(
    ctx,
    path: str,
    verbose: bool,
    yes: bool,
    dry_run: bool,
    json_output: bool,
) -> None:
    """
    Remove venv at specific path.

    Args:
        ctx: Click context
        path: Path to venv directory
        verbose: Show verbose output
        yes: Skip confirmation
        dry_run: Dry run mode
        json_output: Output as JSON
    """
    venv_path_to_remove = Path(path).resolve()

    # Validate path is within prime-uve directory
    try:
        venv_base = get_venv_base_dir()
        if not str(venv_path_to_remove).startswith(str(venv_base)):
            error(f"Path must be within {venv_base}")
            sys.exit(1)
    except Exception as e:
        error(f"Failed to validate path: {e}")
        sys.exit(1)

    # Check if path exists
    if not venv_path_to_remove.exists():
        if json_output:
            print_json({"removed": False, "error": "Path does not exist"})
        else:
            error(f"Path does not exist: {venv_path_to_remove}")
        sys.exit(1)

    # Get size
    size = get_disk_usage(venv_path_to_remove)

    # Show what will be removed
    if not json_output:
        echo(f"Venv path: {venv_path_to_remove}")
        if size > 0:
            echo(f"Size: {format_bytes(size)}")
        echo("")

    # Confirm unless --yes
    if not yes and not dry_run:
        if not click.confirm(f"Remove venv at '{venv_path_to_remove}'?"):
            info("Aborted.")
            return

    if dry_run and not json_output:
        info("[DRY RUN] No changes will be made.")
        echo("")

    # Remove venv
    try:
        if not dry_run:
            shutil.rmtree(venv_path_to_remove)
    except Exception as e:
        if json_output:
            print_json({"removed": False, "error": str(e)})
        else:
            error(f"Failed to remove venv: {e}")
        sys.exit(1)

    # Find and remove from cache if tracked
    if not dry_run:
        try:
            cache = Cache()
            mappings = cache.list_all()
            for project_path, cache_entry in mappings.items():
                cached_venv_expanded = expand_path_variables(cache_entry["venv_path"])
                if cached_venv_expanded == venv_path_to_remove:
                    cache.remove_mapping(Path(project_path))
                    if verbose and not json_output:
                        echo(f"  Removed from cache: {project_path}")
                    break
        except Exception as e:
            if not json_output:
                warning(f"Failed to update cache: {e}")

    # Output results
    if json_output:
        print_json(
            {
                "removed": True,
                "venv_path": str(venv_path_to_remove),
                "size_bytes": size,
            }
        )
    else:
        echo("")
        if dry_run:
            info(f"[DRY RUN] Would remove venv and free {format_bytes(size)}")
        else:
            success(f"Removed venv and freed {format_bytes(size)}")


def prune_command(
    ctx,
    all_venvs: bool,
    orphan: bool,
    current: bool,
    path: Optional[str],
    verbose: bool,
    yes: bool,
    dry_run: bool,
    json_output: bool,
) -> None:
    """
    Clean up venv directories.

    Args:
        ctx: Click context
        all_venvs: Remove all venvs
        orphan: Remove only orphaned venvs
        current: Remove current project's venv
        path: Remove venv at specific path
        verbose: Show verbose output
        yes: Skip confirmation
        dry_run: Dry run mode
        json_output: Output as JSON
    """
    # Validate options - exactly one mode must be specified
    modes = [all_venvs, orphan, current, path is not None]
    if sum(modes) == 0:
        error("Must specify one mode: --all, --orphan, --current, or <path>")
        echo("\nExamples:")
        echo("  prime-uve prune --all          # Remove all venvs")
        echo("  prime-uve prune --orphan       # Remove orphaned venvs only")
        echo("  prime-uve prune --current      # Remove current project's venv")
        echo("  prime-uve prune /path/to/venv  # Remove specific venv")
        sys.exit(1)

    if sum(modes) > 1:
        error("Cannot specify multiple modes")
        sys.exit(1)

    # Dispatch to appropriate handler
    if all_venvs:
        prune_all(ctx, verbose, yes, dry_run, json_output)
    elif orphan:
        prune_orphan(ctx, verbose, yes, dry_run, json_output)
    elif current:
        prune_current(ctx, verbose, yes, dry_run, json_output)
    elif path:
        prune_path(ctx, path, verbose, yes, dry_run, json_output)
