"""Main CLI entry point for prime-uve."""

from pathlib import Path
from typing import Optional

import click

from prime_uve.cli.decorators import common_options, handle_errors


def get_version() -> str:
    """Get version from pyproject.toml."""
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib

    # Find pyproject.toml
    package_root = Path(__file__).parent.parent.parent.parent
    pyproject_path = package_root / "pyproject.toml"

    if pyproject_path.exists():
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
            return data.get("project", {}).get("version", "unknown")

    return "unknown"


@click.group()
@click.version_option(version=get_version(), prog_name="prime-uve")
@click.pass_context
def cli(ctx):
    """
    prime-uve: Virtual environment management for uv with external venv locations.

    Manage Python virtual environments in a centralized location outside your
    project directories. Automatically loads .env.uve files for seamless
    integration with uv.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)


@cli.command()
@click.option("--force", "-f", is_flag=True, help="Reinitialize even if already set up")
@click.option("--venv-dir", type=click.Path(), help="Override venv base directory")
@common_options
@handle_errors
@click.pass_context
def init(
    ctx,
    force: bool,
    venv_dir: Optional[str],
    verbose: bool,
    yes: bool,
    dry_run: bool,
    json_output: bool,
):
    """Initialize project with external venv."""
    from prime_uve.cli.init import init_command

    init_command(ctx, force, venv_dir, verbose, yes, dry_run, json_output)


@cli.command()
@click.option("--orphan-only", is_flag=True, help="Show only orphaned venvs")
@common_options
@handle_errors
@click.pass_context
def list(
    ctx, orphan_only: bool, verbose: bool, yes: bool, dry_run: bool, json_output: bool
):
    """List all managed venvs with validation status."""
    from prime_uve.cli.list import list_command

    list_command(ctx, orphan_only, verbose, yes, dry_run, json_output)


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
        ctx, all_venvs, valid, orphan, current, path, verbose, yes, dry_run, json_output
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


@cli.group()
def configure():
    """Configure integrations (VS Code, etc.)."""
    pass


@configure.command()
@click.option(
    "--workspace", type=click.Path(), help="Specific workspace file to update"
)
@click.option("--create", is_flag=True, help="Create new workspace file")
@common_options
@handle_errors
@click.pass_context
def vscode(
    ctx,
    workspace: Optional[str],
    create: bool,
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

        prime-uve configure vscode --workspace myproject.code-workspace

        prime-uve configure vscode --dry-run          # Preview changes
    """
    from prime_uve.cli.configure import configure_vscode_command

    configure_vscode_command(ctx, workspace, create, verbose, yes, dry_run, json_output)


def main():
    """Main entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
