"""Main CLI entry point for prime-uve."""

import sys
from pathlib import Path
from typing import Optional

import click

from prime_uve.cli.output import error, info
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
@common_options
@handle_errors
@click.pass_context
def list(ctx, verbose: bool, yes: bool, dry_run: bool, json_output: bool):
    """List all managed venvs with validation status."""
    if verbose:
        info("list command - not yet implemented")
    error("Command not implemented yet")
    sys.exit(1)


@cli.command()
@common_options
@handle_errors
@click.pass_context
def prune(ctx, verbose: bool, yes: bool, dry_run: bool, json_output: bool):
    """Clean up venv directories."""
    if verbose:
        info("prune command - not yet implemented")
    error("Command not implemented yet")
    sys.exit(1)


@cli.command()
@common_options
@handle_errors
@click.pass_context
def activate(ctx, verbose: bool, yes: bool, dry_run: bool, json_output: bool):
    """Output activation command for current venv."""
    if verbose:
        info("activate command - not yet implemented")
    error("Command not implemented yet")
    sys.exit(1)


@cli.group()
def configure():
    """Configure integrations (VS Code, etc.)."""
    pass


@configure.command()
@common_options
@handle_errors
@click.pass_context
def vscode(ctx, verbose: bool, yes: bool, dry_run: bool, json_output: bool):
    """Update VS Code workspace with venv path."""
    if verbose:
        info("configure vscode command - not yet implemented")
    error("Command not implemented yet")
    sys.exit(1)


def main():
    """Main entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
