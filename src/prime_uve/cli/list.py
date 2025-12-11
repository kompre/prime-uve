"""List command implementation for prime-uve."""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import click

from prime_uve.cli.output import echo, error, info, print_json, _SYMBOLS
from prime_uve.cli.register import auto_register_current_project
from prime_uve.core.cache import Cache
from prime_uve.core.env_file import read_env_file
from prime_uve.core.paths import expand_path_variables
from prime_uve.utils.disk import format_bytes, get_disk_usage
from prime_uve.utils.venv import find_untracked_venvs, scan_venv_directory


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


def validate_project_mapping(
    project_path: str, cache_entry: dict, calculate_disk_usage: bool = False
) -> ValidationResult:
    """
    Validate a project mapping.

    Simplified validation: Does cached venv_path match UV_PROJECT_ENVIRONMENT in .env.uve?
    - Match → Valid
    - No match (any reason) → Orphan

    Args:
        project_path: Absolute path to project directory
        cache_entry: Cache entry with venv_path, project_name, etc.
        calculate_disk_usage: If True, calculate disk usage (slower). Default False.

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

    # Get disk usage if requested and venv exists
    disk_usage = 0
    if calculate_disk_usage and venv_path_expanded.exists():
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


def supports_hyperlinks() -> bool:
    """Check if the terminal supports OSC 8 hyperlinks."""
    import os

    # Check if we're in a TTY and if terminal supports hyperlinks
    # Windows Terminal, iTerm2, and modern terminals support OSC 8
    if not sys.stdout.isatty():
        return False

    term = os.environ.get("TERM", "")
    term_program = os.environ.get("TERM_PROGRAM", "")
    wt_session = os.environ.get("WT_SESSION", "")

    # Known terminals that support OSC 8
    return bool(
        wt_session  # Windows Terminal
        or term_program in ("iTerm.app", "WezTerm", "vscode")
        or "kitty" in term
        or "alacritty" in term
    )


def make_clickable_path(path: str, display_text: str) -> str:
    """
    Create a clickable terminal hyperlink using OSC 8 escape sequences.

    If terminal doesn't support hyperlinks, returns plain display text.

    Format: \\x1b]8;;file://path\\x1b\\\\display_text\\x1b]8;;\\x1b\\\\

    Args:
        path: Actual file path (for the link)
        display_text: Text to display (can be truncated)

    Returns:
        Formatted string with OSC 8 hyperlink, or plain text if unsupported
    """
    # If terminal doesn't support hyperlinks, return plain text
    if not supports_hyperlinks():
        return display_text

    # Convert Windows path to file:// URL format
    # For UNC paths like \\server\share, use file://server/share
    # For drive paths like C:\path, use file:///C:/path
    if path.startswith("\\\\"):
        # UNC path: \\server\share\path -> file://server/share/path
        file_url = "file:" + path.replace("\\", "/")
    else:
        # Drive path: C:\path -> file:///C:/path
        file_url = "file:///" + path.replace("\\", "/")

    # OSC 8 format: \x1b]8;;URL\x1b\\TEXT\x1b]8;;\x1b\\
    # Using \x1b (ESC) instead of \033 for proper interpretation
    return f"\x1b]8;;{file_url}\x1b\\{display_text}\x1b]8;;\x1b\\"


def truncate_path(path: str, max_length: int, make_clickable: bool = False) -> str:
    """
    Truncate path to fit max_length, keeping most relevant parts.

    Args:
        path: Path string
        max_length: Maximum length
        make_clickable: If True, wrap in OSC 8 hyperlink to full path

    Returns:
        Truncated path (optionally wrapped in hyperlink)
    """
    if len(path) <= max_length:
        return path

    # Try to keep the end (most specific part)
    truncated = "..." + path[-(max_length - 3) :]

    if make_clickable:
        return make_clickable_path(path, truncated)

    return truncated


def get_current_project_root() -> Path | None:
    """Get current project root if in a managed project.

    Returns:
        Path to current project root, or None if not in a project
    """
    try:
        from prime_uve.core.project import find_project_root

        return find_project_root()
    except Exception:
        return None


def output_table(results: list, stats: dict, verbose: bool) -> None:
    """
    Output results as a formatted table.

    Args:
        results: List of validation results (ValidationResult or untracked dicts)
        stats: Statistics dictionary
        verbose: Whether to show verbose output
    """
    echo("Managed Virtual Environments\n")

    # Show legend
    click.secho(
        f"Legend: {_SYMBOLS['success']}: valid | {_SYMBOLS['error']}: orphan | >: current project\n"
    )

    # Get current project root for highlighting
    current_project_root = get_current_project_root()

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

            # Check if this is the current project
            is_current = (
                current_project_root is not None
                and project_path is not None
                and Path(project_path).resolve() == current_project_root.resolve()
            )

            # Use symbols from output module
            status_symbol = _SYMBOLS["success"] if is_valid else _SYMBOLS["error"]
            current_marker = ">" if is_current else " "
            status_text = "Valid" if is_valid else "Orphan"
            size = format_bytes(disk_usage)
            status_display = f"{status_symbol}{current_marker} {status_text}"

            color = "green" if is_valid else "red"
            # Show project name, status, size on first line
            formatted_line = f"{project_name:<20} "
            click.secho(formatted_line, nl=False, bold=is_current)
            click.secho(f"{status_display:<15}", fg=color, nl=False, bold=is_current)
            click.secho(f" {size}", bold=is_current)  # Size on same line

            # Extra details in verbose mode
            if project_path:
                click.secho(f"  Project: {project_path}", bold=is_current)
            click.secho(f"  Venv:    {venv_path_expanded}", bold=is_current)
            if hash_val:
                click.secho(f"  Hash:    {hash_val}", bold=is_current)
            if created_at:
                click.secho(f"  Created: {created_at}", bold=is_current)

            if not is_valid and venv_path:
                click.secho(f"  Cache:     {venv_path}", bold=is_current)
                click.secho(
                    f"  .env.uve:  {env_venv_path or 'Not found (or path mismatch)'}",
                    bold=is_current,
                )
            echo("")
    else:
        # Compact format - new column order: STATUS | PROJECT PATH | VENV PATH
        # Define column widths as constants
        STATUS_WIDTH = 7
        PROJECT_PATH_WIDTH = 60

        header = f"{'STATUS':<{STATUS_WIDTH}} {'PROJECT PATH':<{PROJECT_PATH_WIDTH}} {'VENV PATH'}"
        echo(header)
        echo("-" * 140)  # Wider separator for new format

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
            project_path = (
                result.project_path
                if hasattr(result, "project_path")
                else result.get("project_path")
            )

            # Check if this is the current project
            is_current = (
                current_project_root is not None
                and project_path is not None
                and Path(project_path).resolve() == current_project_root.resolve()
            )

            # Use symbols from output module - compact status
            status_symbol = _SYMBOLS["success"] if is_valid else _SYMBOLS["error"]
            current_marker = ">" if is_current else " "
            status_display = f"{status_symbol}{current_marker}"

            # Prepare project path display (truncate if needed, make clickable)
            project_path_str = str(project_path) if project_path else "N/A"
            # Truncate to width - 2 to leave room for "..." prefix
            max_truncate_length = PROJECT_PATH_WIDTH - 2
            needs_truncation = (
                project_path and len(project_path_str) > PROJECT_PATH_WIDTH
            )

            if needs_truncation:
                # Truncate and make clickable
                truncated_text = truncate_path(
                    project_path_str, max_truncate_length, make_clickable=False
                )
                project_path_display = make_clickable_path(
                    project_path_str, truncated_text
                )
                # For visible length: "..." (3) + remaining chars = max_truncate_length
                visible_length = len(truncated_text)
            else:
                # Short enough, make clickable without truncation
                if project_path:
                    project_path_display = make_clickable_path(
                        project_path_str, project_path_str
                    )
                else:
                    project_path_display = project_path_str
                visible_length = len(project_path_str)

            # Calculate padding needed to reach PROJECT_PATH_WIDTH
            padding_needed = PROJECT_PATH_WIDTH - visible_length

            # Make venv path clickable
            venv_path_str = str(venv_path_expanded)
            venv_path_display = make_clickable_path(venv_path_str, venv_path_str)

            color = "green" if is_valid else "red"

            # Format: STATUS | PROJECT PATH | VENV PATH
            # Build styled components with proper padding
            status_styled = click.style(
                f"{status_display:<{STATUS_WIDTH}}",
                fg=color,
                bold=is_current,
            )

            # Project path with padding and clickable link
            # Note: click.style() doesn't work with hyperlinks, so we use manual ANSI codes
            project_path_padded = f"{project_path_display}{' ' * padding_needed}"
            if is_current:
                project_path_styled = f"\x1b[1m{project_path_padded}\x1b[0m"
            else:
                project_path_styled = project_path_padded

            # Venv path with clickable link
            if is_current:
                venv_path_styled = f"\x1b[1m{venv_path_display}\x1b[0m"
            else:
                venv_path_styled = venv_path_display

            # Output all columns in one call with proper spacing
            click.echo(f"{status_styled} {project_path_styled} {venv_path_styled}")

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
    no_auto_register: bool,
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
        no_auto_register: Skip automatic registration of current project
        verbose: Show verbose output
        yes: Skip confirmations (unused here)
        dry_run: Dry run mode (unused here)
        json_output: Output as JSON
    """
    # 0. Auto-register current project if present (unless --no-auto-register)
    if not no_auto_register:
        try:
            cache = Cache()
            was_registered, project_name = auto_register_current_project(cache)
            if was_registered and not json_output:
                info(f"Registered current project '{project_name}' in cache")
        except Exception:
            # Continue even if auto-registration fails
            pass

    # 1. Load cache
    try:
        cache = Cache()
        mappings = cache.list_all()
    except Exception as e:
        error(f"Failed to load cache: {e}")
        sys.exit(1)

    # 2. Validate all cached mappings
    # Only calculate disk usage when it will be displayed (verbose or JSON mode)
    calculate_sizes = verbose or json_output

    results = []
    for project_path, cache_entry in mappings.items():
        result = validate_project_mapping(
            project_path, cache_entry, calculate_disk_usage=calculate_sizes
        )
        results.append(result)

    # 3. Find and add untracked venvs as orphans
    untracked_venvs = find_untracked_venvs(mappings, calculate_disk_usage=calculate_sizes)
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
