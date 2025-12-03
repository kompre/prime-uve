# Task 3.1: CLI Framework Setup

**Phase**: 3 (CLI Commands)
**Priority**: High (blocks all other CLI tasks)
**Estimated Complexity**: Medium
**Status**: Proposal

## Objective

Set up the Click-based CLI framework with consistent error handling, output formatting, and common options. This provides the foundation for all `prime-uve` subcommands.

## Dependencies

**Requires**:
- Task 1.1: Path Hashing System ✅
- Task 1.2: Cache System ✅
- Task 1.3: .env.uve File Management ✅
- Task 1.4: Project Detection ✅

**Blocks**:
- Task 3.2: `prime-uve init`
- Task 3.3: `prime-uve list`
- Task 3.4: `prime-uve prune`
- Task 3.5: `prime-uve activate`
- Task 3.6: `prime-uve configure vscode`

## Background

The CLI framework establishes patterns and utilities used across all subcommands:
- Consistent error messaging
- Colored output (success/warning/error)
- Common options (--verbose, --yes, --dry-run)
- Version command
- Help text formatting

Using Click provides:
- Automatic help generation
- Type validation
- Nested command groups
- Testing utilities

## Requirements

### Functional Requirements

1. **Main CLI Group**:
   - Command: `prime-uve`
   - Shows help with all subcommands
   - Displays version with `--version` flag
   - Sets up global options (--verbose)

2. **Common Options**:
   - `--verbose` / `-v`: Enable verbose output
   - `--yes` / `-y`: Skip confirmation prompts
   - `--dry-run`: Show what would happen without executing
   - `--json`: Output in JSON format (where applicable)

3. **Output Formatting**:
   - Success messages (green ✓)
   - Warnings (yellow ⚠)
   - Errors (red ✗)
   - Info messages (blue ℹ)
   - Consistent indentation and spacing

4. **Error Handling**:
   - Exit codes: 0 (success), 1 (user error), 2 (system error)
   - Clear error messages with actionable suggestions
   - Stack traces only in verbose mode
   - Context for errors (which file, path, etc.)

5. **Version Command**:
   - `prime-uve --version` shows version from pyproject.toml
   - Format: `prime-uve version X.Y.Z`

### Non-Functional Requirements

- **Usability**: Help text is clear and includes examples
- **Consistency**: All commands follow same patterns
- **Performance**: CLI startup < 100ms
- **Testing**: Click testing utilities for all commands

## Implementation Plan

### 1. Project Structure

```
src/prime_uve/cli/
├── __init__.py          # Export main CLI
├── main.py              # Click group, version command, global options
├── output.py            # Output formatting utilities
├── errors.py            # Custom exceptions, error handlers
├── options.py           # Reusable Click options/decorators
└── utils.py             # Common utilities (confirm prompts, etc.)
```

### 2. Main CLI Setup (main.py)

```python
"""Main CLI entry point for prime-uve."""
import click
from importlib.metadata import version

from prime_uve.cli import output
from prime_uve.cli.errors import handle_errors


@click.group()
@click.version_option(version("prime-uve"), prog_name="prime-uve")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """prime-uve: External venv management for uv projects.

    Manages Python virtual environments in a centralized location
    outside your project directories.

    Examples:
        prime-uve init              Initialize external venv for current project
        prime-uve list              List all managed venvs
        prime-uve prune --orphan    Clean up orphaned venvs
        prime-uve activate          Get activation command for current venv
    """
    # Store global state in context
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    output.set_verbose(verbose)


def main() -> None:
    """Entry point for prime-uve command."""
    cli(obj={})


if __name__ == "__main__":
    main()
```

### 3. Output Formatting (output.py)

```python
"""Output formatting utilities."""
import sys
import click
from typing import Any

_verbose = False


def set_verbose(verbose: bool) -> None:
    """Set verbose mode globally."""
    global _verbose
    _verbose = verbose


def success(message: str) -> None:
    """Print success message (green checkmark)."""
    click.secho(f"✓ {message}", fg="green")


def error(message: str) -> None:
    """Print error message (red X)."""
    click.secho(f"✗ {message}", fg="red", err=True)


def warning(message: str) -> None:
    """Print warning message (yellow warning)."""
    click.secho(f"⚠ {message}", fg="yellow")


def info(message: str) -> None:
    """Print info message (blue i)."""
    click.secho(f"ℹ {message}", fg="blue")


def verbose(message: str) -> None:
    """Print message only in verbose mode."""
    if _verbose:
        click.echo(f"  {message}", err=True)


def table(headers: list[str], rows: list[list[str]]) -> None:
    """Print formatted table."""
    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

    # Print header
    header_row = "  ".join(h.ljust(w) for h, w in zip(headers, widths))
    click.echo(header_row)
    click.echo("─" * len(header_row))

    # Print rows
    for row in rows:
        click.echo("  ".join(str(c).ljust(w) for c, w in zip(row, widths)))


def json_output(data: Any) -> None:
    """Print JSON output."""
    import json
    click.echo(json.dumps(data, indent=2))
```

### 4. Error Handling (errors.py)

```python
"""Error handling utilities."""
import sys
import click
import traceback
from typing import NoReturn

from prime_uve.cli import output


class CliError(Exception):
    """Base exception for CLI errors."""

    exit_code = 1

    def __init__(self, message: str, hint: str | None = None):
        self.message = message
        self.hint = hint
        super().__init__(message)


class UserError(CliError):
    """User error (invalid input, missing file, etc)."""
    exit_code = 1


class SystemError(CliError):
    """System error (permission denied, disk full, etc)."""
    exit_code = 2


def handle_error(e: Exception, verbose: bool = False) -> NoReturn:
    """Handle exception and exit with appropriate code."""
    if isinstance(e, CliError):
        output.error(e.message)
        if e.hint:
            output.info(f"Hint: {e.hint}")
        if verbose:
            traceback.print_exc()
        sys.exit(e.exit_code)

    elif isinstance(e, click.ClickException):
        # Let Click handle its own exceptions
        raise

    else:
        # Unexpected error
        output.error(f"Unexpected error: {e}")
        if verbose:
            traceback.print_exc()
        else:
            output.info("Run with --verbose for more details")
        sys.exit(2)


def confirm(message: str, default: bool = False, yes_flag: bool = False) -> bool:
    """Prompt for confirmation unless --yes flag is set."""
    if yes_flag:
        return True
    return click.confirm(message, default=default)
```

### 5. Reusable Options (options.py)

```python
"""Reusable Click options and decorators."""
import click
from functools import wraps


def common_options(f):
    """Decorator to add common options to commands."""
    @click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompts")
    @click.option("--dry-run", is_flag=True, help="Show what would happen without executing")
    @wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper


def json_option(f):
    """Decorator to add --json option."""
    @click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
    @wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper
```

### 6. Testing Setup

```python
# tests/cli/conftest.py
"""Test fixtures for CLI tests."""
import pytest
from click.testing import CliRunner


@pytest.fixture
def cli_runner():
    """Provide Click CLI runner."""
    return CliRunner()


@pytest.fixture
def isolated_cli(cli_runner, tmp_path, monkeypatch):
    """Provide CLI runner in isolated filesystem."""
    monkeypatch.chdir(tmp_path)
    return cli_runner
```

```python
# tests/cli/test_main.py
"""Test main CLI entry point."""
from click.testing import CliRunner
from prime_uve.cli.main import cli


def test_version(cli_runner):
    """Test --version flag."""
    result = cli_runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "prime-uve version" in result.output


def test_help(cli_runner):
    """Test --help flag."""
    result = cli_runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "prime-uve" in result.output
    assert "init" in result.output  # Subcommand should be listed


def test_verbose_flag(cli_runner):
    """Test --verbose flag sets context."""
    result = cli_runner.invoke(cli, ["--verbose", "--help"])
    assert result.exit_code == 0
```

## Acceptance Criteria

### Must Have

- ✅ `prime-uve --version` shows version from pyproject.toml
- ✅ `prime-uve --help` shows all subcommands
- ✅ `prime-uve --verbose` enables verbose output globally
- ✅ Success messages use green ✓
- ✅ Error messages use red ✗ and go to stderr
- ✅ Warning messages use yellow ⚠
- ✅ Info messages use blue ℹ
- ✅ Exit codes: 0 (success), 1 (user error), 2 (system error)
- ✅ `--yes` flag skips confirmation prompts
- ✅ `--dry-run` flag shows actions without executing
- ✅ Click test runner available for all command tests
- ✅ Consistent error message format

### Should Have

- ✅ Table formatting utility for list commands
- ✅ JSON output utility
- ✅ Context manager for temp state (verbose, yes, dry-run)
- ✅ Common decorators for reusable options

### Nice to Have

- Colored help text with examples
- Shell completion support (Click >= 8.0)
- Progress bars for long operations

## Testing Strategy

### Unit Tests

```python
# Test output formatting
def test_success_message()
def test_error_message()
def test_warning_message()
def test_info_message()
def test_verbose_output()
def test_table_formatting()
def test_json_output()

# Test error handling
def test_user_error_handling()
def test_system_error_handling()
def test_unexpected_error_handling()
def test_click_exception_passthrough()

# Test CLI setup
def test_version_command()
def test_help_text()
def test_verbose_flag()
def test_global_context()
```

### Integration Tests

- Test CLI invocation via subprocess
- Test output capture (stdout/stderr)
- Test exit codes
- Test option combinations (--verbose --yes)

## Dependencies

**Python Packages**:
```toml
dependencies = [
    "click>=8.0.0",
    "filelock>=3.0.0",  # Already added
]
```

**Development Dependencies**:
```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
]
```

## Rollout Plan

1. ✅ Create package structure (`cli/` directory)
2. ✅ Implement `main.py` with Click group
3. ✅ Implement `output.py` with formatting utilities
4. ✅ Implement `errors.py` with error handling
5. ✅ Implement `options.py` with reusable decorators
6. ✅ Add version command reading from pyproject.toml
7. ✅ Write unit tests for all utilities
8. ✅ Test CLI invocation and help text
9. ✅ Update pyproject.toml entry point if needed
10. ✅ Documentation in docstrings and help text

## Success Metrics

- ✅ All unit tests pass (target: 15+ tests)
- ✅ 100% coverage of CLI framework code
- ✅ Help text is clear and includes examples
- ✅ Error messages are actionable
- ✅ Consistent output formatting across all commands
- ✅ CLI startup time < 100ms

## Future Enhancements

1. **Shell Completion**: Add Click shell completion for bash/zsh/fish
2. **Color Themes**: Support NO_COLOR env var, custom themes
3. **Progress Bars**: For long operations (init, prune --all)
4. **Config File**: Support ~/.prime-uve/config.toml for defaults
5. **Plugin System**: Allow custom subcommands

## References

- [Click Documentation](https://click.palletsprojects.com/)
- [Click Testing](https://click.palletsprojects.com/en/8.1.x/testing/)
- Architecture Design: `_todo/pending/architecture-design.md` (Section 5)

## Notes

- This task is intentionally minimal - just the framework
- Subcommands (init, list, prune, etc.) are separate tasks
- Focus on establishing patterns that all commands will follow
- Keep the framework simple and extensible
