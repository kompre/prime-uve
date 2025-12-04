"""Output formatting utilities for CLI."""

import json as json_module
import sys
from typing import Any, Dict

import click


def success(message: str) -> None:
    """Print success message in green."""
    click.secho(f"✓ {message}", fg="green")


def error(message: str) -> None:
    """Print error message in red."""
    click.secho(f"✗ {message}", fg="red", err=True)


def warning(message: str) -> None:
    """Print warning message in yellow."""
    click.secho(f"⚠ {message}", fg="yellow")


def info(message: str) -> None:
    """Print info message in blue."""
    click.secho(f"ℹ {message}", fg="blue")


def print_json(data: Dict[str, Any]) -> None:
    """Print data as formatted JSON."""
    click.echo(json_module.dumps(data, indent=2))


def confirm(message: str, default: bool = False, yes_flag: bool = False) -> bool:
    """
    Prompt user for confirmation.

    Args:
        message: The confirmation message to display
        default: Default value if user just presses Enter
        yes_flag: If True, skip prompt and return True (from --yes flag)

    Returns:
        True if confirmed, False otherwise
    """
    if yes_flag:
        return True

    return click.confirm(message, default=default)


def echo(message: str, **kwargs) -> None:
    """
    Print message (wrapper around click.echo for consistency).

    Args:
        message: The message to print
        **kwargs: Additional arguments to pass to click.echo
    """
    click.echo(message, **kwargs)
