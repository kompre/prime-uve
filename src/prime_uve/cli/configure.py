"""Configure IDE and tool integration."""

import sys
from pathlib import Path

import click

from prime_uve.cli.output import confirm, echo, error, info, print_json, success, warning
from prime_uve.core.env_file import read_env_file
from prime_uve.core.paths import expand_path_variables
from prime_uve.core.project import find_project_root
from prime_uve.utils.vscode import (
    create_default_workspace,
    find_workspace_files,
    read_workspace,
    update_python_interpreter,
    write_workspace,
)


def _get_interpreter_path(venv_path: Path) -> Path:
    """Get platform-specific Python interpreter path.

    Args:
        venv_path: Path to virtual environment

    Returns:
        Path to Python interpreter executable
    """
    if sys.platform == "win32":
        return venv_path / "Scripts" / "python.exe"
    else:
        return venv_path / "bin" / "python"


def _prompt_workspace_choice(workspace_files: list[Path], project_root: Path) -> Path | None:
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
        "Which workspace should be updated? [1-{}, 0 to cancel]".format(len(workspace_files)),
        type=str,
        default="1"
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
        verbose: Show detailed output
        yes: Skip confirmations
        dry_run: Show what would be done
        json_output: Output as JSON

    Raises:
        ValueError: If project not initialized or venv not found
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

    venv_path_expanded = expand_path_variables(venv_path_var)

    if not venv_path_expanded.exists():
        raise ValueError(
            f"Venv not found\n"
            f"Expected venv at: {venv_path_expanded}\n\n"
            f"To recreate: Run 'prime-uve init --force'"
        )

    # 3. Determine interpreter path (platform-specific)
    interpreter_path = _get_interpreter_path(venv_path_expanded)

    if not interpreter_path.exists():
        raise ValueError(
            f"Python interpreter not found: {interpreter_path}\n"
            f"Venv may be corrupted.\n\n"
            f"Run 'prime-uve init --force' to recreate."
        )

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
    else:
        # Auto-discover workspace files
        workspace_files = find_workspace_files(project_root)

        if not workspace_files:
            # No workspace files found
            if not create and not confirm(
                "No workspace file found. Create one?",
                default=True,
                yes_flag=yes
            ):
                raise click.Abort()

            # Create new workspace
            workspace_file = project_root / f"{project_root.name}.code-workspace"
            workspace_data = create_default_workspace(project_root, interpreter_path)

            if verbose:
                info(f"Creating workspace: {workspace_file}")
                info(f"Interpreter: {interpreter_path}")

            if not dry_run:
                write_workspace(workspace_file, workspace_data)
                success(f"Created {workspace_file.name}")
                success("Python interpreter set to venv")
                echo("\nTo use:")
                echo(f"  1. Open workspace: code {workspace_file.name}")
                echo("  2. VS Code will load with correct interpreter")
            else:
                echo(f"[DRY RUN] Would create: {workspace_file}")
                echo(f"[DRY RUN] Interpreter: {interpreter_path}")

            workspace_created = True

            if json_output:
                print_json({
                    "workspace_file": str(workspace_file),
                    "created": True,
                    "updated": False,
                    "interpreter_path": str(interpreter_path),
                    "previous_interpreter": None
                })

            return

        elif len(workspace_files) > 1:
            # Multiple files - prompt user
            workspace_file = _prompt_workspace_choice(workspace_files, project_root)
            if workspace_file is None:
                raise click.Abort()
        else:
            # Single file found
            workspace_file = workspace_files[0]

    # 5. Update workspace file
    if verbose:
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
        backup_path = workspace_file.with_suffix('.code-workspace.bak')
        workspace_file.rename(backup_path)
        info(f"Backed up to: {backup_path}")

        # Create new workspace
        workspace_data = create_default_workspace(project_root, interpreter_path)
        workspace_created = True

    # Check if interpreter already set
    current_interpreter = workspace_data.get("settings", {}).get("python.defaultInterpreterPath")

    if current_interpreter and current_interpreter != str(interpreter_path) and not yes:
        echo(f"\nCurrent interpreter: {current_interpreter}")
        echo(f"New interpreter:     {interpreter_path}")
        if not confirm("\nUpdate workspace?", default=True, yes_flag=yes):
            raise click.Abort()

    # Update settings
    workspace_data = update_python_interpreter(workspace_data, interpreter_path)

    # Write changes
    if dry_run:
        echo(f"[DRY RUN] Would update workspace: {workspace_file.name}")
        echo("\n[DRY RUN] Changes:")
        echo(f"  settings.python.defaultInterpreterPath:")
        echo(f"    Old: {current_interpreter or '(not set)'}")
        echo(f"    New: {interpreter_path}")
    else:
        write_workspace(workspace_file, workspace_data)
        success(f"Updated {workspace_file.name}")
        success("Python interpreter set to venv")
        echo("\nVS Code will detect the change automatically if open.")
        echo("If not, restart VS Code or reload the window.")

    if json_output:
        print_json({
            "workspace_file": str(workspace_file),
            "created": workspace_created,
            "updated": not workspace_created,
            "interpreter_path": str(interpreter_path),
            "previous_interpreter": current_interpreter
        })
