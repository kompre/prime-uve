"""CLI decorators for common options and error handling."""

import functools
import sys
import traceback
from typing import Callable

import click

from prime_uve.cli.output import error, info


def common_options(func: Callable) -> Callable:
    """
    Decorator to add common CLI options to commands.

    Adds:
        --verbose: Enable verbose output
        --yes: Skip confirmation prompts
        --dry-run: Show what would be done without doing it
        --json: Output results as JSON
    """
    func = click.option(
        "--json",
        "json_output",
        is_flag=True,
        help="Output results as JSON",
    )(func)
    func = click.option(
        "--dry-run",
        is_flag=True,
        help="Show what would be done without doing it",
    )(func)
    func = click.option(
        "--yes",
        "-y",
        is_flag=True,
        help="Skip confirmation prompts",
    )(func)
    func = click.option(
        "--verbose",
        "-v",
        is_flag=True,
        help="Enable verbose output",
    )(func)
    return func


def handle_errors(func: Callable) -> Callable:
    """
    Decorator to handle errors and exit with appropriate codes.

    Exit codes:
        0: Success
        1: User error (invalid input, missing file, etc.)
        2: System error (unexpected exception, permission denied, etc.)
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except click.ClickException:
            # Let Click handle its own exceptions
            raise
        except click.Abort:
            # User cancelled (Ctrl+C)
            error("Cancelled by user")
            sys.exit(1)
        except FileNotFoundError as e:
            error(f"File not found: {e}")
            sys.exit(1)
        except PermissionError as e:
            error(f"Permission denied: {e}")
            sys.exit(2)
        except ValueError as e:
            error(f"Invalid value: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            error("Interrupted by user")
            sys.exit(1)
        except Exception as e:
            # Get verbose flag from context if available
            ctx = click.get_current_context(silent=True)
            verbose = False
            if ctx and hasattr(ctx, "params"):
                verbose = ctx.params.get("verbose", False)

            error(f"Unexpected error: {e}")

            if verbose:
                info("Full traceback:")
                traceback.print_exc()

            sys.exit(2)

    return wrapper
