"""Output formatting utilities for CLI."""

import json as json_module
import sys
from typing import Any, Dict

import click


# Use ASCII-safe symbols on Windows to avoid encoding issues
def _get_symbols():
    """Get symbols based on platform."""
    if sys.platform == "win32":
        return {
            "success": "[OK]",
            "error": "[!]",
            "warning": "[!]",
            "info": "[i]",
        }
    else:
        return {
            "success": "✓",
            "error": "✗",
            "warning": "⚠",
            "info": "ℹ",
        }


_SYMBOLS = _get_symbols()


def success(message: str) -> None:
    """Print success message in green."""
    click.secho(f"{_SYMBOLS['success']} {message}", fg="green")


def error(message: str) -> None:
    """Print error message in red."""
    click.secho(f"{_SYMBOLS['error']} {message}", fg="red", err=True)


def warning(message: str) -> None:
    """Print warning message in yellow."""
    click.secho(f"{_SYMBOLS['warning']} {message}", fg="yellow")


def info(message: str) -> None:
    """Print info message in blue."""
    click.secho(f"{_SYMBOLS['info']} {message}", fg="blue")


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
