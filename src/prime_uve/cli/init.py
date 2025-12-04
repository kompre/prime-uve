"""Initialize project with external venv management."""

import click

from prime_uve.cli.output import confirm, echo, info, success
from prime_uve.core.cache import Cache
from prime_uve.core.env_file import (
    read_env_file,
    update_env_file_preserve_format,
)
from prime_uve.core.paths import (
    expand_path_variables,
    generate_hash,
    generate_venv_path,
)
from prime_uve.core.project import find_project_root, get_project_metadata


def init_command(
    ctx: click.Context,
    force: bool,
    venv_dir: str | None,
    verbose: bool,
    yes: bool,
    dry_run: bool,
    json_output: bool,
) -> None:
    """Initialize project with external venv management.

    Args:
        ctx: Click context
        force: Reinitialize even if already set up
        venv_dir: Override venv base directory
        verbose: Show detailed output
        yes: Skip confirmations
        dry_run: Show what would be done
        json_output: Output as JSON

    Raises:
        ValueError: If not in a project or other validation errors
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

    # 2. Get project metadata
    metadata = get_project_metadata(project_root)
    project_name = metadata.name or project_root.name

    # 3. Check if already initialized
    # Only block if UV_PROJECT_ENVIRONMENT is already set
    env_file = project_root / ".env.uve"
    if env_file.exists() and not force:
        existing_vars = read_env_file(env_file)
        existing_venv = existing_vars.get("UV_PROJECT_ENVIRONMENT")

        if existing_venv:
            # Already initialized - UV_PROJECT_ENVIRONMENT is set
            raise ValueError(
                f"Project already initialized\n"
                f"UV_PROJECT_ENVIRONMENT is already set in .env.uve\n\n"
                f"Current venv: {existing_venv}\n\n"
                f"To reinitialize: Run 'prime-uve init --force'\n"
                f"Note: --force will only update UV_PROJECT_ENVIRONMENT, other variables will be preserved"
            )
        # If .env.uve exists but UV_PROJECT_ENVIRONMENT is not set, we can initialize

    # 4. Confirm force if overwriting
    if force and env_file.exists():
        existing_vars = read_env_file(env_file)
        old_venv = existing_vars.get("UV_PROJECT_ENVIRONMENT", "(not set)")
        new_venv = generate_venv_path(project_root)

        if old_venv != new_venv and not yes:
            other_vars_count = len(
                [k for k in existing_vars.keys() if k != "UV_PROJECT_ENVIRONMENT"]
            )
            preservation_note = (
                f"\n  {other_vars_count} other variable(s) will be preserved"
                if other_vars_count > 0
                else ""
            )

            if not confirm(
                f"⚠ Warning: Forcing reinitialization\n"
                f"  This will update UV_PROJECT_ENVIRONMENT in .env.uve\n"
                f"  Old venv: {old_venv}\n"
                f"  New venv: {new_venv}{preservation_note}\n\n"
                f"Continue?",
                default=False,
                yes_flag=yes,
            ):
                raise click.Abort()

    # 5. Generate venv path (always uses ${HOME})
    # Note: venv_dir parameter is currently not supported by generate_venv_path
    # For now, ignore the --venv-dir option
    venv_path = generate_venv_path(project_root)
    venv_path_expanded = expand_path_variables(venv_path)
    path_hash = generate_hash(project_root)

    if verbose:
        info(f"Project name: {project_name}")
        info(f"Project root: {project_root}")
        info(f"Venv path (variable form): {venv_path}")
        info(f"Venv path (expanded): {venv_path_expanded}")
        info(f"Path hash: {path_hash}")

    # 6. Dry run output
    if dry_run:
        echo(f"[DRY RUN] Would initialize project: {project_name}")
        echo(
            f"[DRY RUN] Would create: .env.uve with UV_PROJECT_ENVIRONMENT={venv_path}"
        )
        echo(f"[DRY RUN] Would add cache entry: {project_root} -> {venv_path}")
        return

    # 7. Create/update .env.uve
    # Use update_env_file_preserve_format to preserve file structure, comments, and order
    update_env_file_preserve_format(env_file, {"UV_PROJECT_ENVIRONMENT": venv_path})

    # 8. Add to cache
    cache = Cache()
    cache.add_mapping(project_root, venv_path, project_name, path_hash)

    # 9. Output results
    if json_output:
        import json

        result = {
            "status": "success",
            "project": {
                "name": project_name,
                "root": str(project_root),
                "pyproject": (project_root / "pyproject.toml").exists(),
            },
            "venv": {
                "path": venv_path,
                "path_expanded": str(venv_path_expanded),
                "hash": path_hash,
            },
            "env_file": {
                "path": str(env_file),
                "created": True,
            },
            "cache": {"added": True},
        }
        echo(json.dumps(result, indent=2))
    else:
        success(f"Project: {project_name}")
        success(f"Project root: {project_root}")
        success(f"Venv path: {venv_path}")
        success("Created .env.uve")
        success("Added to cache")

        echo("\nNext steps:")
        echo("  1. Use 'uve' instead of 'uv' for all commands")
        echo("  2. Run 'uve sync' to create venv and install dependencies")
        echo("  3. Commit .env.uve to version control")
        echo("\nExample:")
        echo("  uve sync                # Creates venv and installs dependencies")
        echo("  uve add requests        # Add a package")
        echo("  uve run python app.py   # Run your application")
