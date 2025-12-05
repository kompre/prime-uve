"""Register command implementation for prime-uve."""

import click

from prime_uve.cli.output import confirm, echo, info, print_json, success
from prime_uve.core.cache import Cache
from prime_uve.core.env_file import read_env_file
from prime_uve.core.paths import expand_path_variables, generate_hash
from prime_uve.core.project import find_project_root, get_project_metadata


def auto_register_current_project(cache: Cache) -> bool:
    """Silently register current project if in a managed project.

    Called internally by list/prune commands before executing.
    Uses minimal validation - trusts .env.uve as source of truth.

    Args:
        cache: Cache instance to register with

    Returns:
        True if registered, False if nothing to register
    """
    try:
        # Find project root (same logic as uve wrapper)
        project_root = find_project_root()
        if not project_root:
            return False  # Not in a project

        # Check for .env.uve
        env_file = project_root / ".env.uve"
        if not env_file.exists():
            return False  # No .env.uve

        # Read UV_PROJECT_ENVIRONMENT
        env_vars = read_env_file(env_file)
        venv_path = env_vars.get("UV_PROJECT_ENVIRONMENT")
        if not venv_path or not venv_path.strip():
            return False  # Not set or empty

        # Get metadata from pyproject.toml (same as init)
        metadata = get_project_metadata(project_root)
        project_name = metadata.name or project_root.name
        path_hash = generate_hash(project_root)

        # Register with cache (idempotent operation)
        cache.add_mapping(project_root, venv_path, project_name, path_hash)
        return True

    except Exception:
        # Silent failure - don't break list/prune
        return False


def register_command(
    ctx: click.Context,
    verbose: bool,
    yes: bool,
    dry_run: bool,
    json_output: bool,
) -> None:
    """Register current project with cache from existing .env.uve.

    Args:
        ctx: Click context
        verbose: Show detailed output
        yes: Skip confirmations
        dry_run: Show what would be done
        json_output: Output as JSON

    Raises:
        ValueError: If not in a project or .env.uve issues
        click.Abort: If user cancels operation
    """
    # 1. Find project root
    project_root = find_project_root()
    if not project_root:
        raise ValueError(
            "Not in a Python project\n"
            "Could not find pyproject.toml in current directory or any parent directory.\n\n"
            "To fix: Run this command from a directory containing pyproject.toml"
        )

    # 2. Check if .env.uve exists
    env_file = project_root / ".env.uve"
    if not env_file.exists():
        raise ValueError(
            ".env.uve file not found\n"
            "The .env.uve file does not exist in the project root.\n\n"
            "To fix: Run 'prime-uve init' to initialize this project"
        )

    # 3. Read .env.uve and extract UV_PROJECT_ENVIRONMENT
    env_vars = read_env_file(env_file)
    venv_path = env_vars.get("UV_PROJECT_ENVIRONMENT")

    if not venv_path or not venv_path.strip():
        raise ValueError(
            "UV_PROJECT_ENVIRONMENT not set in .env.uve\n"
            "The UV_PROJECT_ENVIRONMENT variable is missing or empty.\n\n"
            "To fix: Run 'prime-uve init' to set up this project"
        )

    # 4. Get project metadata from pyproject.toml (same as init does)
    metadata = get_project_metadata(project_root)
    project_name = metadata.name or project_root.name
    path_hash = generate_hash(project_root)
    venv_path_expanded = expand_path_variables(venv_path)

    if verbose:
        info(f"Project name: {project_name}")
        info(f"Project root: {project_root}")
        info(f"Venv path: {venv_path}")
        info(f"Venv path (expanded): {venv_path_expanded}")
        info(f"Path hash: {path_hash}")

    # 5. Check if already in cache
    cache = Cache()
    existing_mapping = cache.get_mapping(project_root)

    if existing_mapping:
        # Already registered - check if it matches
        cached_venv_path = existing_mapping["venv_path"]

        if cached_venv_path == venv_path:
            # Already registered with same venv path
            if json_output:
                print_json(
                    {
                        "status": "already_registered",
                        "project_name": project_name,
                        "venv_path": venv_path,
                    }
                )
            else:
                info("Project already registered with matching venv path")
                success(f"Project: {project_name}")
                success(f"Venv: {venv_path}")
            return
        else:
            # Registered but with different venv path - confirm update
            if not yes and not dry_run:
                if not confirm(
                    f"Cache venv path will be updated:\n"
                    f"  Old: {cached_venv_path}\n"
                    f"  New: {venv_path}\n"
                    f"Continue?",
                    default=True,
                    yes_flag=yes,
                ):
                    raise click.Abort()

    # 6. Dry run output
    if dry_run:
        echo(f"[DRY RUN] Would register: {project_name}")
        echo(f"[DRY RUN] Cache entry: {project_root} -> {venv_path}")
        return

    # 7. Register with cache
    cache.add_mapping(project_root, venv_path, project_name, path_hash)

    # 8. Output results
    if json_output:
        print_json(
            {
                "status": "registered",
                "project_name": project_name,
                "project_root": str(project_root),
                "venv_path": venv_path,
                "venv_path_expanded": str(venv_path_expanded),
                "hash": path_hash,
            }
        )
    else:
        if existing_mapping:
            success("Updated cache registration")
        else:
            success("Registered project with cache")
        success(f"Project: {project_name}")
        success(f"Venv: {venv_path}")
        info(f"  Expanded: {venv_path_expanded}")
