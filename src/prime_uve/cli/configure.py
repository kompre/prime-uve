"""Configure IDE and tool integration."""

import sys
from pathlib import Path

import click

from prime_uve.cli.output import confirm, echo, error, info, print_json, success
from prime_uve.core.env_file import read_env_file, update_env_file
from prime_uve.core.paths import expand_path_variables
from prime_uve.core.project import find_project_root
from prime_uve.utils.vscode import (
    absolute_to_vscode_path,
    create_default_workspace,
    deep_merge_dicts,
    find_default_workspace,
    find_workspace_files,
    get_platform_suffix,
    get_workspace_filename,
    read_workspace,
    update_workspace_settings,
    write_workspace,
    escape_env_variables,
)


def _get_interpreter_path(venv_path: Path) -> Path:
    """Get platform-specific Python interpreter path (expanded).

    Args:
        venv_path: Expanded path to virtual environment

    Returns:
        Path to Python interpreter executable
    """

    if sys.platform == "win32":
        return venv_path / "Scripts" / "python.exe"
    else:
        return venv_path / "bin" / "python"


def _get_interpreter_path_variable_form(venv_path_var: str) -> str:
    """Get platform-specific Python interpreter path with environment variables.

    This preserves environment variables like ${HOME} for cross-platform
    compatibility in VS Code workspace files.

    Args:
        venv_path_var: Venv path with environment variables (e.g., ${HOME}/...)

    Returns:
        Interpreter path with environment variables preserved
    """
    # Normalize path separators and ensure no trailing slash
    venv_path_var = venv_path_var.rstrip("/\\")

    if sys.platform == "win32":
        # Use forward slashes for consistency in VS Code
        return escape_env_variables(f"{venv_path_var}/Scripts/python.exe").replace(
            "HOME", "USERPROFILE"
        )
    else:
        return escape_env_variables(f"{venv_path_var}/bin/python")


def _prompt_workspace_choice(
    workspace_files: list[Path], project_root: Path
) -> Path | None:
    """Prompt user to select a workspace file.

    Args:
        workspace_files: List of available workspace files
        project_root: Project root path for relative display

    Returns:
        Selected workspace file path, or None if cancelled
    """
    echo("Multiple workspace files found:\n")
    for i, wf in enumerate(workspace_files, 1):
        try:
            relative = wf.relative_to(project_root)
        except ValueError:
            relative = wf
        echo(f"  [{i}] {relative}")

    echo("")
    choice_str = click.prompt(
        "Which workspace should be updated? [1-{}, 0 to cancel]".format(
            len(workspace_files)
        ),
        type=str,
        default="1",
    )

    try:
        choice = int(choice_str)
        if choice == 0:
            return None
        if 1 <= choice <= len(workspace_files):
            return workspace_files[choice - 1]
    except (ValueError, IndexError):
        pass

    error(f"Invalid choice: {choice_str}")
    return None


def configure_vscode_command(
    ctx: click.Context,
    workspace_path: str | None,
    create: bool,
    suffix: str | None,
    merge: str | None,
    expand: bool,
    export_as_default: str | None,
    verbose: bool,
    yes: bool,
    dry_run: bool,
    json_output: bool,
) -> None:
    """Update VS Code workspace with venv path.

    Args:
        ctx: Click context
        workspace_path: Specific workspace file to update
        create: Force creation of new workspace
        suffix: Create platform-specific workspace file with suffix (None or "__auto__" for OS name)
        merge: Merge settings from another workspace (None, "__default__" for default, or path)
        expand: Use fully expanded absolute paths instead of VS Code variables
        export_as_default: Save workspace as default in .env.uve ("__merge__" to use merge source, or path)
        verbose: Show detailed output
        yes: Skip confirmations
        dry_run: Show what would be done
        json_output: Output as JSON

    Raises:
        ValueError: If project not initialized or venv not found
        click.Abort: If user cancels operation
    """
    # Validate --merge requires --suffix
    if merge is not None and suffix is None:
        raise ValueError(
            "--merge option requires --suffix\n"
            "The merge option is only meaningful when creating platform-specific workspace files.\n\n"
            "Usage: prime-uve configure vscode --suffix --merge [FILE]"
        )

    # Validate --export-as-default with __merge__ requires --merge
    if export_as_default == "__merge__" and merge is None:
        raise ValueError(
            "--export-as-default (without value) requires --merge\n"
            "To export the merge source as default, use both options together.\n\n"
            "Usage: prime-uve configure vscode --suffix --merge <file> --export-as-default"
        )

    # Resolve suffix if __auto__
    if suffix == "__auto__":
        suffix = get_platform_suffix()
    # 1. Find project root
    project_root = find_project_root()
    if not project_root:
        raise ValueError(
            "Not in a Python project\n"
            "Could not find pyproject.toml in current directory or any parent directory.\n\n"
            "To fix: Run this command from a directory containing pyproject.toml"
        )

    # 2. Find .env.uve and extract venv path
    env_file = project_root / ".env.uve"
    if not env_file.exists():
        raise ValueError(
            "Project not initialized\n"
            "No .env.uve file found.\n\n"
            "Run 'prime-uve init' to initialize the project."
        )

    env_vars = read_env_file(env_file)
    venv_path_var = env_vars.get("UV_PROJECT_ENVIRONMENT")
    if not venv_path_var:
        raise ValueError(
            ".env.uve missing UV_PROJECT_ENVIRONMENT\n\n"
            "Run 'prime-uve init --force' to reinitialize."
        )

    # Get default workspace from .env.uve if set
    default_workspace = env_vars.get("PRIMEUVE_DEFAULT_CW")

    venv_path_expanded = expand_path_variables(venv_path_var)

    if not venv_path_expanded.exists():
        raise ValueError(
            f"Venv not found\n"
            f"Expected venv at: {venv_path_expanded}\n\n"
            f"To recreate: Run 'prime-uve init --force'"
        )

    # 3. Determine interpreter path (platform-specific)
    # Use expanded path for validation
    interpreter_path_expanded = _get_interpreter_path(venv_path_expanded)

    if not interpreter_path_expanded.exists():
        raise ValueError(
            f"Python interpreter not found: {interpreter_path_expanded}\n"
            f"Venv may be corrupted.\n\n"
            f"Run 'prime-uve init --force' to recreate."
        )

    # Determine interpreter path format based on --expand flag
    if expand:
        # Use fully expanded absolute path
        interpreter_path = str(interpreter_path_expanded).replace("\\", "/")
    else:
        # Use VS Code variables for cross-platform compatibility
        interpreter_path = absolute_to_vscode_path(interpreter_path_expanded)

    # 4. Find or create workspace file
    workspace_file: Path | None = None
    workspace_created = False

    if workspace_path:
        # User specified a workspace file
        workspace_file = Path(workspace_path)
        if not workspace_file.is_absolute():
            workspace_file = project_root / workspace_file

        if not workspace_file.exists() and not create:
            raise ValueError(f"Workspace file not found: {workspace_file}")

        # If suffix provided, create suffixed version based on specified file
        if suffix:
            workspace_file = get_workspace_filename(
                project_root, suffix, workspace_file
            )
    else:
        # Auto-discover workspace files
        workspace_files = find_workspace_files(project_root)

        if suffix:
            # When suffix is provided, we want to create/update a suffixed file
            # Use the first existing workspace as a base, or project name if none exist
            existing_workspace = workspace_files[0] if workspace_files else None
            workspace_file = get_workspace_filename(
                project_root, suffix, existing_workspace
            )

            # Check if the suffixed file exists
            if workspace_file.exists():
                # Suffixed file exists - we'll update it
                workspace_data = read_workspace(workspace_file)
                workspace_created = False
            else:
                # Suffixed file doesn't exist - create it
                workspace_created = True
                if merge is not None:
                    # When merging, start with minimal workspace
                    # (merge will add settings from source file)
                    workspace_data = create_default_workspace(
                        project_root, interpreter_path
                    )
                elif existing_workspace and existing_workspace.exists():
                    # Copy settings from existing workspace
                    workspace_data = read_workspace(existing_workspace)
                else:
                    # Create new workspace
                    workspace_data = create_default_workspace(
                        project_root, interpreter_path
                    )
        elif not workspace_files:
            # No workspace files found
            if not create and not confirm(
                "No workspace file found. Create one?", default=True, yes_flag=yes
            ):
                raise click.Abort()

            # Create new workspace
            workspace_file = get_workspace_filename(project_root, None, None)
            workspace_data = create_default_workspace(project_root, interpreter_path)

        # Handle suffix workspace (both create and update)
        if suffix:
            if verbose and not json_output:
                action = "Creating" if workspace_created else "Updating"
                info(f"{action} workspace: {workspace_file}")
                info(f"Interpreter: {interpreter_path}")

            # Handle merge if requested
            if merge is not None:
                # Resolve merge source
                if merge == "__default__":
                    # First check if PRIMEUVE_DEFAULT_CW is set in .env.uve
                    if default_workspace:
                        merge_source = Path(default_workspace)
                        if not merge_source.is_absolute():
                            merge_source = project_root / merge_source
                        if verbose and not json_output:
                            info(
                                f"Using default workspace from .env.uve: {merge_source.name}"
                            )
                    else:
                        # Fall back to auto-detection
                        merge_source = find_default_workspace(
                            project_root, workspace_files
                        )
                        if merge_source is None:
                            raise ValueError(
                                "No default workspace found to merge from\n"
                                "Cannot determine which workspace to merge.\n\n"
                                "Specify a workspace file explicitly with --merge <file> or set default with --export-as-default"
                            )
                else:
                    # User specified a file
                    merge_source = Path(merge)
                    if not merge_source.is_absolute():
                        merge_source = project_root / merge_source

                if not merge_source.exists():
                    raise ValueError(
                        f"Merge source not found: {merge_source}\n\n"
                        f"Ensure the workspace file exists before merging."
                    )

                # Don't merge from the same file
                if merge_source.resolve() == workspace_file.resolve():
                    raise ValueError(
                        f"Cannot merge workspace into itself\n"
                        f"Merge source and target are the same file: {workspace_file.name}"
                    )

                # Read and merge (merge_data takes precedence over existing workspace_data)
                merge_data = read_workspace(merge_source)
                workspace_data = deep_merge_dicts(workspace_data, merge_data)

                if verbose and not json_output:
                    info(f"Merged settings from: {merge_source.name}")

            # Handle export-as-default
            if export_as_default is not None:
                # Determine which workspace to export as default
                if export_as_default == "__merge__":
                    # Use merge source as default
                    if merge is None:
                        # This should be caught by validation, but double-check
                        raise ValueError(
                            "Cannot export merge source as default without --merge"
                        )
                    default_to_export = merge_source
                else:
                    # User specified a workspace file
                    default_to_export = Path(export_as_default)
                    if not default_to_export.is_absolute():
                        default_to_export = project_root / default_to_export

                    # Validate the file exists
                    if not default_to_export.exists():
                        raise ValueError(
                            f"Cannot export as default: {default_to_export}\n\n"
                            f"The specified workspace file does not exist."
                        )

                # Get relative path if within project, otherwise absolute
                try:
                    relative_path = default_to_export.relative_to(project_root)
                    workspace_to_save = str(relative_path)
                except ValueError:
                    # Not relative to project root, use absolute path
                    workspace_to_save = str(default_to_export)

                # Write to .env.uve
                if not dry_run:
                    update_env_file(
                        env_file, {"PRIMEUVE_DEFAULT_CW": workspace_to_save}
                    )
                    if verbose and not json_output:
                        info(f"Set default workspace in .env.uve: {workspace_to_save}")
                else:
                    echo(
                        f"[DRY RUN] Would set PRIMEUVE_DEFAULT_CW={workspace_to_save} in .env.uve"
                    )

            # Update interpreter path in the workspace data
            workspace_data = update_workspace_settings(workspace_data, interpreter_path)

            if not dry_run:
                write_workspace(workspace_file, workspace_data)
                if not json_output:
                    success("VS Code workspace configured")
                    echo(f"\nWorkspace: {workspace_file.name}")
                    echo("\nSettings applied:")
                    echo(f"  ✓ Python interpreter: {interpreter_path}")
                    if export_as_default is not None:
                        echo("  ✓ Default workspace saved to .env.uve")
                    echo("\nNext steps:")
                    echo("  1. Open workspace in VS Code:")
                    echo(f"     code {workspace_file.name}")
                    echo("\n  2. Reload window if already open:")
                    echo('     Ctrl+Shift+P → "Developer: Reload Window"')
            else:
                if not json_output:
                    action = "create" if workspace_created else "update"
                    echo(f"[DRY RUN] Would {action}: {workspace_file}")
                    echo(f"[DRY RUN] Interpreter: {interpreter_path}")
                    if export_as_default is not None:
                        echo("[DRY RUN] Would set default workspace in .env.uve")

            if json_output:
                print_json(
                    {
                        "workspace_file": str(workspace_file),
                        "created": workspace_created,
                        "updated": not workspace_created,
                        "interpreter_path": str(interpreter_path),
                        "previous_interpreter": None,
                    }
                )

            return

        elif not workspace_files and not suffix:
            # Original logic for creating workspace without suffix
            if verbose and not json_output:
                info(f"Creating workspace: {workspace_file}")
                info(f"Interpreter: {interpreter_path}")

            if not dry_run:
                write_workspace(workspace_file, workspace_data)
                if not json_output:
                    success("VS Code workspace configured")
                    echo(f"\nWorkspace: {workspace_file.name}")
                    echo("\nSettings applied:")
                    echo(f"  ✓ Python interpreter: {interpreter_path}")
                    echo("\nNext steps:")
                    echo("  1. Open workspace in VS Code:")
                    echo(f"     code {workspace_file.name}")
                    echo("\n  2. Reload window if already open:")
                    echo('     Ctrl+Shift+P → "Developer: Reload Window"')
                    echo("\n  3. Open new terminal (Ctrl+`):")
                    echo(f"     Should show: ({project_root.name}) in prompt")
                    echo("\n  4. If interpreter not detected:")
                    echo('     Ctrl+Shift+P → "Python: Select Interpreter"')
            else:
                if not json_output:
                    echo(f"[DRY RUN] Would create: {workspace_file}")
                    echo(f"[DRY RUN] Interpreter: {interpreter_path}")

            workspace_created = True

            if json_output:
                print_json(
                    {
                        "workspace_file": str(workspace_file),
                        "created": True,
                        "updated": False,
                        "interpreter_path": str(interpreter_path),
                        "previous_interpreter": None,
                    }
                )

            return

        elif len(workspace_files) > 1 and not suffix:
            # Multiple files - prompt user
            workspace_file = _prompt_workspace_choice(workspace_files, project_root)
            if workspace_file is None:
                raise click.Abort()
        else:
            # Single file found
            workspace_file = workspace_files[0]

    # 5. Update workspace file
    if verbose and not json_output:
        info(f"Workspace: {workspace_file}")
        info(f"Interpreter: {interpreter_path}")

    # Read existing workspace
    try:
        workspace_data = read_workspace(workspace_file)
    except ValueError as e:
        # Malformed JSON
        if not yes:
            warning_msg = (
                f"Warning: {e}\n"
                f"The workspace file appears to be malformed.\n\n"
                f"Create a backup and regenerate workspace file?"
            )
            if not confirm(warning_msg, default=True, yes_flag=yes):
                raise click.Abort()

        # Backup existing file
        backup_path = workspace_file.with_suffix(".code-workspace.bak")
        workspace_file.rename(backup_path)
        info(f"Backed up to: {backup_path}")

        # Create new workspace
        workspace_data = create_default_workspace(project_root, interpreter_path)
        workspace_created = True

    # Check if interpreter already set
    current_interpreter = workspace_data.get("settings", {}).get(
        "python.defaultInterpreterPath"
    )

    if current_interpreter and current_interpreter != str(interpreter_path) and not yes:
        echo(f"\nCurrent interpreter: {current_interpreter}")
        echo(f"New interpreter:     {interpreter_path}")
        if not confirm("\nUpdate workspace?", default=True, yes_flag=yes):
            raise click.Abort()

    # Update settings
    workspace_data = update_workspace_settings(workspace_data, interpreter_path)

    # Handle export-as-default (for non-suffix workspaces)
    if export_as_default is not None and not suffix:
        # User must specify a workspace file explicitly
        default_to_export = Path(export_as_default)
        if not default_to_export.is_absolute():
            default_to_export = project_root / default_to_export

        # Validate the file exists
        if not default_to_export.exists():
            raise ValueError(
                f"Cannot export as default: {default_to_export}\n\n"
                f"The specified workspace file does not exist."
            )

        # Get relative path if within project, otherwise absolute
        try:
            relative_path = default_to_export.relative_to(project_root)
            workspace_to_save = str(relative_path)
        except ValueError:
            # Not relative to project root, use absolute path
            workspace_to_save = str(default_to_export)

        # Write to .env.uve
        if not dry_run:
            update_env_file(env_file, {"PRIMEUVE_DEFAULT_CW": workspace_to_save})
            if verbose and not json_output:
                info(f"Set default workspace in .env.uve: {workspace_to_save}")
        else:
            echo(
                f"[DRY RUN] Would set PRIMEUVE_DEFAULT_CW={workspace_to_save} in .env.uve"
            )

    # Write changes
    if dry_run:
        if not json_output:
            echo(f"[DRY RUN] Would update workspace: {workspace_file.name}")
            echo("\n[DRY RUN] Changes:")
            echo("  settings.python.defaultInterpreterPath:")
            echo(f"    Old: {current_interpreter or '(not set)'}")
            echo(f"    New: {interpreter_path}")
            echo("  settings.python.terminal.activateEnvironment: true")
            echo('  settings.python.envFile: "${workspaceFolder}/.env.uve"')
            if export_as_default is not None:
                echo("\n[DRY RUN] Would set default workspace in .env.uve")
    else:
        write_workspace(workspace_file, workspace_data)
        if not json_output:
            success("VS Code workspace configured")
            echo(f"\nWorkspace: {workspace_file.name}")
            echo("\nSettings applied:")
            echo(f"  ✓ Python interpreter: {interpreter_path}")
            if export_as_default is not None:
                echo("  ✓ Default workspace saved to .env.uve")
            echo("\nNext steps:")
            echo("  1. Open workspace in VS Code:")
            echo(f"     code {workspace_file.name}")
            echo("\n  2. Reload window if already open:")
            echo('     Ctrl+Shift+P → "Developer: Reload Window"')
            echo("\n  3. Open new terminal (Ctrl+`):")
            echo(f"     Should show: ({project_root.name}) in prompt")
            echo("\n  4. If interpreter not detected:")
            echo('     Ctrl+Shift+P → "Python: Select Interpreter"')

    if json_output:
        print_json(
            {
                "workspace_file": str(workspace_file),
                "created": workspace_created,
                "updated": not workspace_created,
                "interpreter_path": str(interpreter_path),
                "previous_interpreter": current_interpreter,
            }
        )
