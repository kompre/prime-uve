"""Main CLI entry point for prime-uve."""

from typing import Optional

import click

from prime_uve import __version__
from prime_uve.cli.decorators import common_options, handle_errors


@click.group()
@click.version_option(version=__version__, prog_name="prime-uve")
@click.pass_context
def cli(ctx):
    """Virtual environment management for uv with external venv locations.

    Manage Python virtual environments in a centralized location outside your
    project directories. Automatically loads .env.uve files for seamless
    integration with uv.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)


# Dynamically update the help text to include version
cli.help = f"prime-uve v{__version__}: {cli.help}"


@cli.command()
@click.option("--force", "-f", is_flag=True, help="Reinitialize even if already set up")
@click.option("--venv-dir", type=click.Path(), help="Override venv base directory")
@click.option("--sync", is_flag=True, help="Run 'uve sync' after initialization")
@common_options
@handle_errors
@click.pass_context
def init(
    ctx,
    force: bool,
    venv_dir: Optional[str],
    sync: bool,
    verbose: bool,
    yes: bool,
    dry_run: bool,
    json_output: bool,
):
    """Initialize project with external venv."""
    from prime_uve.cli.init import init_command

    init_command(ctx, force, venv_dir, sync, verbose, yes, dry_run, json_output)


@cli.command()
@click.option("--orphan-only", is_flag=True, help="Show only orphaned venvs")
@click.option(
    "--no-auto-register",
    is_flag=True,
    help="Skip automatic registration of current project",
)
@common_options
@handle_errors
@click.pass_context
def list(
    ctx,
    orphan_only: bool,
    no_auto_register: bool,
    verbose: bool,
    yes: bool,
    dry_run: bool,
    json_output: bool,
):
    """List all managed venvs with validation status."""
    from prime_uve.cli.list import list_command

    list_command(ctx, orphan_only, no_auto_register, verbose, yes, dry_run, json_output)


@cli.command()
@click.option(
    "--all", "all_venvs", is_flag=True, help="Remove ALL venvs (tracked and untracked)"
)
@click.option(
    "--valid", is_flag=True, help="Remove only valid venvs (cache matches .env.uve)"
)
@click.option(
    "--orphan",
    is_flag=True,
    help="Remove only orphaned venvs (cache mismatch or untracked)",
)
@click.option("--current", is_flag=True, help="Remove current project's venv")
@click.option(
    "--no-auto-register",
    is_flag=True,
    help="Skip automatic registration of current project",
)
@click.argument("path", required=False, type=click.Path())
@common_options
@handle_errors
@click.pass_context
def prune(
    ctx,
    all_venvs: bool,
    valid: bool,
    orphan: bool,
    current: bool,
    no_auto_register: bool,
    path: Optional[str],
    verbose: bool,
    yes: bool,
    dry_run: bool,
    json_output: bool,
):
    """Clean up venv directories.

    Must specify one mode:
    - --all: Remove ALL venvs (both tracked and untracked)
    - --valid: Remove only valid venvs (cache matches .env.uve)
    - --orphan: Remove only orphaned venvs (cache mismatch or untracked)
    - --current: Remove venv for current project
    - <path>: Remove venv at specific path
    """
    from prime_uve.cli.prune import prune_command

    prune_command(
        ctx,
        all_venvs,
        valid,
        orphan,
        current,
        no_auto_register,
        path,
        verbose,
        yes,
        dry_run,
        json_output,
    )


@cli.command()
@click.option("--shell", type=str, help="Shell type (bash, zsh, fish, pwsh, cmd)")
@common_options
@handle_errors
@click.pass_context
def activate(
    ctx,
    shell: Optional[str],
    verbose: bool,
    yes: bool,
    dry_run: bool,
    json_output: bool,
):
    """Output activation command for current venv.

    Generates shell-specific commands to export all variables from .env.uve
    and activate the project's venv.

    Usage:
        eval "$(prime-uve activate)"           # Bash/Zsh
        eval (prime-uve activate | psub)       # Fish
        Invoke-Expression (prime-uve activate) # PowerShell

    Supported shells: bash, zsh, fish, pwsh, cmd
    """
    from prime_uve.cli.activate import activate_command

    activate_command(ctx, shell, verbose, yes, dry_run, json_output)


@cli.command()
@click.option("--shell", type=str, help="Shell to spawn (bash, zsh, fish, pwsh, cmd)")
@common_options
@handle_errors
@click.pass_context
def shell(
    ctx,
    shell: Optional[str],
    verbose: bool,
    yes: bool,
    dry_run: bool,
    json_output: bool,
):
    """Spawn a new shell with venv activated.

    Starts a new shell session with:
      • All variables from .env.uve loaded
      • Virtual environment activated
      • Prompt showing venv name

    Usage:
        prime-uve shell           # Auto-detect shell
        prime-uve shell --shell bash  # Force specific shell

    Type 'exit' to leave the activated shell and return to your original shell.
    """
    from prime_uve.cli.shell import shell_command

    shell_command(ctx, shell, verbose, yes, dry_run, json_output)


@cli.command()
@common_options
@handle_errors
@click.pass_context
def register(
    ctx,
    verbose: bool,
    yes: bool,
    dry_run: bool,
    json_output: bool,
):
    """Register current project with cache from existing .env.uve.

    This command reads the existing .env.uve file and ensures the project
    is properly tracked in cache.json. Useful for fixing cache desync issues.

    The cache is automatically kept in sync when running 'prime-uve list' or
    'prime-uve prune' from within a project, so manual registration is rarely
    needed. Use this command for verbose feedback or when troubleshooting.

    Usage:
        prime-uve register           # Register current project
        prime-uve register --dry-run # Preview what would be registered
        prime-uve register --verbose # Show detailed information
    """
    from prime_uve.cli.register import register_command

    register_command(ctx, verbose, yes, dry_run, json_output)


@cli.command(name="dir")
@common_options
@handle_errors
@click.pass_context
def dir_command(
    ctx,
    verbose: bool,
    yes: bool,
    dry_run: bool,
    json_output: bool,
):
    """Open the venvs base directory in file explorer.

    Opens the centralized location where all virtual environments are stored:
    ${HOME}/.prime-uve/venvs

    Usage:
        prime-uve dir         # Open venvs directory
        prime-uve dir --verbose # Show path before opening
    """
    from prime_uve.cli.dir import dir_command as dir_cmd

    dir_cmd(ctx, verbose, yes, dry_run, json_output)


@cli.group()
def configure():
    """Configure integrations (VS Code, etc.)."""
    pass


@configure.command()
@click.option(
    "--workspace", type=click.Path(), help="Specific workspace file to update"
)
@click.option("--create", is_flag=True, help="Create new workspace file")
@click.option(
    "--suffix",
    is_flag=False,
    flag_value="__auto__",
    help="Create platform-specific workspace with suffix (uses OS name if no value given)",
)
@click.option(
    "--merge",
    is_flag=False,
    flag_value="__default__",
    help="Merge settings from another workspace file (requires --suffix; uses default workspace if no value given)",
)
@click.option(
    "--expand",
    is_flag=True,
    default=False,
    help="Use fully expanded absolute paths instead of VS Code variables",
)
@click.option(
    "--export-as-default",
    is_flag=False,
    flag_value="__merge__",
    help="Save workspace as default in .env.uve (uses --merge source if provided, otherwise specify file)",
)
@common_options
@handle_errors
@click.pass_context
def vscode(
    ctx,
    workspace: Optional[str],
    create: bool,
    suffix: Optional[str],
    merge: Optional[str],
    expand: bool,
    export_as_default: Optional[str],
    verbose: bool,
    yes: bool,
    dry_run: bool,
    json_output: bool,
):
    """Update VS Code workspace with venv path.

    This sets the Python interpreter in your workspace settings so VS Code
    can provide IntelliSense, debugging, and other IDE features with your
    external venv.

    If no workspace file exists, one will be created.

    Examples:

        prime-uve configure vscode                    # Update or create workspace

        prime-uve configure vscode --suffix           # Create platform-specific workspace (e.g., project.linux.code-workspace)

        prime-uve configure vscode --suffix dev       # Create workspace with custom suffix

        prime-uve configure vscode --suffix --merge   # Create platform-specific workspace, merge from default workspace

        prime-uve configure vscode --suffix --merge joe.code-workspace  # Merge settings from joe.code-workspace

        prime-uve configure vscode --expand           # Use absolute paths instead of variables

        prime-uve configure vscode --workspace myproject.code-workspace

        prime-uve configure vscode --export-as-default myproject.code-workspace  # Set default workspace for merging

        prime-uve configure vscode --suffix --merge joe.code-workspace --export-as-default  # Merge from joe.code-workspace and set as default

        prime-uve configure vscode --dry-run          # Preview changes
    """
    from prime_uve.cli.configure import configure_vscode_command

    configure_vscode_command(
        ctx,
        workspace,
        create,
        suffix,
        merge,
        expand,
        export_as_default,
        verbose,
        yes,
        dry_run,
        json_output,
    )


def main():
    """Main entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
