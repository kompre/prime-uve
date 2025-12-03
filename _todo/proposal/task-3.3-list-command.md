# Task 3.3: Implement `prime-uve list`

**Phase**: 3 (CLI Commands)
**Priority**: Medium (useful for management)
**Estimated Complexity**: Low
**Status**: Proposal

## Objective

Implement the `prime-uve list` command to display all tracked virtual environments with validation status. This helps users see which venvs exist, which are orphaned, and which have mismatched paths.

## Dependencies

**Requires**:
- Task 1.2: Cache System ✅
- Task 1.3: .env.uve File Management ✅
- Task 3.1: CLI Framework Setup ⏳

**Blocks**:
- None (independent of other commands)

## Background

`prime-uve list` provides visibility into all managed venvs by:
1. Reading the cache to get all tracked projects
2. Validating each mapping against the filesystem
3. Displaying status in a formatted table or JSON

This is useful for:
- Seeing all projects using prime-uve
- Identifying orphaned venvs (project deleted)
- Detecting path mismatches (.env.uve changed manually)
- Getting a quick overview of disk usage

## Requirements

### Functional Requirements

1. **List All Venvs**:
   - Read cache and get all mappings
   - Validate each mapping using `Cache.validate_mapping()`
   - Display in table format (default) or JSON

2. **Validation Status**:
   - ✓ Valid: Project exists, venv exists, .env.uve matches
   - ✗ Orphaned: Project or venv missing
   - ⚠ Mismatch: .env.uve path differs from cache
   - ❌ Error: Unexpected error during validation

3. **Table Output**:
   - Columns: PROJECT, VENV, STATUS
   - Truncate long paths with ellipsis
   - Color-code status (green/red/yellow/red)
   - Sort by project name (alphabetical)

4. **JSON Output**:
   - `--json` flag outputs structured data
   - Include all fields (project, venv, status, timestamps)
   - Machine-readable for scripting

5. **Filtering**:
   - `--orphan-only` shows only orphaned venvs
   - `--valid-only` shows only valid venvs
   - `--invalid-only` shows invalid or mismatch

6. **Empty State**:
   - If no venvs tracked, show helpful message
   - Suggest running `prime-uve init`

### Non-Functional Requirements

- **Performance**: List 100+ venvs in < 2 seconds
- **Usability**: Clear visual distinction between statuses
- **Reliability**: Handle corrupted cache gracefully

## Implementation Plan

### 1. Command Structure

```python
# src/prime_uve/cli/list.py
"""prime-uve list command."""
import click
from pathlib import Path

from prime_uve.cli import output, errors, options
from prime_uve.core.cache import Cache, ValidationStatus


@click.command(name="list")
@click.option("--orphan-only", is_flag=True, help="Show only orphaned venvs")
@click.option("--valid-only", is_flag=True, help="Show only valid venvs")
@click.option("--invalid-only", is_flag=True, help="Show invalid or mismatched venvs")
@options.json_option
@click.pass_context
def list_command(
    ctx: click.Context,
    orphan_only: bool,
    valid_only: bool,
    invalid_only: bool,
    json_output: bool
) -> None:
    """List all managed venvs with validation status.

    Shows project path, venv location, and validation status for each
    tracked virtual environment.

    Status indicators:
        ✓ Valid     - Project exists, venv exists, paths match
        ✗ Orphaned  - Project or venv deleted
        ⚠ Mismatch  - .env.uve path differs from cache
        ❌ Error    - Validation error

    Examples:
        prime-uve list                  List all venvs
        prime-uve list --orphan-only    Show orphaned venvs
        prime-uve list --json           Output as JSON
    """
    verbose = ctx.obj.get("verbose", False)

    try:
        # Validate conflicting flags
        if sum([orphan_only, valid_only, invalid_only]) > 1:
            raise errors.UserError(
                "Cannot combine --orphan-only, --valid-only, and --invalid-only",
                hint="Use only one filter flag"
            )

        # Load cache
        output.verbose("Loading cache...")
        cache = Cache()
        mappings = cache.list_all()

        if not mappings:
            if json_output:
                output.json_output({"venvs": []})
            else:
                output.info("No venvs tracked yet")
                output.info("Run 'prime-uve init' in a project to get started")
            return

        # Validate all mappings
        output.verbose(f"Validating {len(mappings)} venv(s)...")
        results = []
        for project_path in mappings:
            validation = cache.validate_mapping(Path(project_path))
            results.append({
                "project": project_path,
                "venv": mappings[project_path]["venv_path"],
                "venv_expanded": mappings[project_path]["venv_path_expanded"],
                "status": validation.status.value,
                "message": validation.message,
                "created_at": mappings[project_path].get("created_at"),
                "last_validated": mappings[project_path].get("last_validated"),
            })

        # Apply filters
        if orphan_only:
            results = [r for r in results if r["status"] == "orphaned"]
        elif valid_only:
            results = [r for r in results if r["status"] == "valid"]
        elif invalid_only:
            results = [r for r in results if r["status"] in ["orphaned", "mismatch", "error"]]

        # Sort alphabetically by project
        results.sort(key=lambda r: r["project"])

        # Output
        if json_output:
            output.json_output({"venvs": results, "count": len(results)})
        else:
            _print_table(results)

            # Summary
            total = len(results)
            valid = sum(1 for r in results if r["status"] == "valid")
            orphaned = sum(1 for r in results if r["status"] == "orphaned")
            mismatch = sum(1 for r in results if r["status"] == "mismatch")
            error = sum(1 for r in results if r["status"] == "error")

            output.info("")
            output.info(f"Total: {total} | Valid: {valid} | Orphaned: {orphaned} | Mismatch: {mismatch} | Error: {error}")

    except errors.CliError:
        raise
    except Exception as e:
        errors.handle_error(e, verbose)


def _print_table(results: list[dict]) -> None:
    """Print results as formatted table."""
    if not results:
        output.info("No venvs found matching filter")
        return

    # Prepare rows
    headers = ["PROJECT", "VENV", "STATUS"]
    rows = []

    for r in results:
        # Truncate long paths
        project = _truncate_path(r["project"], 40)
        venv = _truncate_path(r["venv"], 40)

        # Format status with color
        status = _format_status(r["status"], r.get("message"))

        rows.append([project, venv, status])

    # Print table using framework utility
    output.table(headers, rows)


def _truncate_path(path: str, max_len: int) -> str:
    """Truncate path with ellipsis if too long."""
    if len(path) <= max_len:
        return path

    # Try to keep filename visible
    parts = path.split("/")
    if len(parts[-1]) < max_len - 3:
        # Keep last part
        return "..." + path[-(max_len-3):]
    else:
        # Just truncate
        return path[:max_len-3] + "..."


def _format_status(status: str, message: str | None = None) -> str:
    """Format status with color and icon."""
    if status == "valid":
        return click.style("✓ Valid", fg="green")
    elif status == "orphaned":
        msg = f"✗ Orphaned"
        if message:
            msg += f" ({message})"
        return click.style(msg, fg="red")
    elif status == "mismatch":
        return click.style("⚠ Mismatch", fg="yellow")
    elif status == "error":
        msg = "❌ Error"
        if message:
            msg += f" ({message})"
        return click.style(msg, fg="red")
    else:
        return status
```

### 2. Table Formatting Examples

#### All Venvs
```
$ prime-uve list

PROJECT                                  VENV                                      STATUS
──────────────────────────────────────────────────────────────────────────────────────────
/home/user/projects/my-app               ${HOME}/prime-uve/venvs/my-app_a1b2...   ✓ Valid
/home/user/projects/old-project          ${HOME}/prime-uve/venvs/old-proj...      ✗ Orphaned (project deleted)
/home/user/projects/test-app             ${HOME}/prime-uve/venvs/test-app...      ⚠ Mismatch

Total: 3 | Valid: 1 | Orphaned: 1 | Mismatch: 1 | Error: 0
```

#### Orphaned Only
```
$ prime-uve list --orphan-only

PROJECT                                  VENV                                      STATUS
──────────────────────────────────────────────────────────────────────────────────────────
/home/user/projects/old-project          ${HOME}/prime-uve/venvs/old-proj...      ✗ Orphaned (project deleted)

Total: 1 | Valid: 0 | Orphaned: 1 | Mismatch: 0 | Error: 0
```

#### JSON Output
```
$ prime-uve list --json
{
  "venvs": [
    {
      "project": "/home/user/projects/my-app",
      "venv": "${HOME}/prime-uve/venvs/my-app_a1b2c3d4",
      "venv_expanded": "/home/user/prime-uve/venvs/my-app_a1b2c3d4",
      "status": "valid",
      "message": null,
      "created_at": "2025-12-03T12:00:00Z",
      "last_validated": "2025-12-03T12:30:00Z"
    }
  ],
  "count": 1
}
```

#### Empty State
```
$ prime-uve list

ℹ No venvs tracked yet
ℹ Run 'prime-uve init' in a project to get started
```

### 3. Testing

```python
# tests/cli/test_list.py
"""Test prime-uve list command."""
import pytest
import json
from click.testing import CliRunner
from pathlib import Path

from prime_uve.cli.main import cli
from prime_uve.core.cache import Cache


def test_list_empty(isolated_cli, tmp_path):
    """Test list with no venvs."""
    result = isolated_cli.invoke(cli, ["list"])
    assert result.exit_code == 0
    assert "No venvs tracked" in result.output


def test_list_basic(isolated_cli, tmp_path, monkeypatch):
    """Test list with valid venv."""
    # Setup cache
    cache = Cache()
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text('[project]\nname="test"')
    (project / ".env.uve").write_text("UV_PROJECT_ENVIRONMENT=${HOME}/venvs/test")

    venv = tmp_path / "venvs" / "test"
    venv.mkdir(parents=True)

    cache.add_mapping(project, "${HOME}/venvs/test", "test")

    # Test
    result = isolated_cli.invoke(cli, ["list"])
    assert result.exit_code == 0
    assert "Valid" in result.output
    assert str(project) in result.output


def test_list_orphaned(isolated_cli, tmp_path):
    """Test list with orphaned venv."""
    # Setup cache with deleted project
    cache = Cache()
    project = tmp_path / "deleted-project"
    cache.add_mapping(project, "${HOME}/venvs/test", "test")

    result = isolated_cli.invoke(cli, ["list"])
    assert result.exit_code == 0
    assert "Orphaned" in result.output


def test_list_json(isolated_cli, tmp_path):
    """Test JSON output."""
    result = isolated_cli.invoke(cli, ["list", "--json"])
    assert result.exit_code == 0

    data = json.loads(result.output)
    assert "venvs" in data
    assert "count" in data
    assert isinstance(data["venvs"], list)


def test_list_orphan_only_filter(isolated_cli, tmp_path):
    """Test --orphan-only filter."""
    cache = Cache()

    # Valid project
    project1 = tmp_path / "valid"
    project1.mkdir()
    (project1 / "pyproject.toml").touch()
    (project1 / ".env.uve").write_text("UV_PROJECT_ENVIRONMENT=${HOME}/venvs/valid")
    venv1 = tmp_path / "venvs" / "valid"
    venv1.mkdir(parents=True)
    cache.add_mapping(project1, "${HOME}/venvs/valid", "valid")

    # Orphaned project
    project2 = tmp_path / "orphaned"
    cache.add_mapping(project2, "${HOME}/venvs/orphaned", "orphaned")

    result = isolated_cli.invoke(cli, ["list", "--orphan-only"])
    assert result.exit_code == 0
    assert "orphaned" in result.output.lower()
    assert "valid" not in result.output.lower()


def test_list_conflicting_filters(isolated_cli):
    """Test error with conflicting filter flags."""
    result = isolated_cli.invoke(cli, ["list", "--orphan-only", "--valid-only"])
    assert result.exit_code == 1
    assert "Cannot combine" in result.output
```

## Acceptance Criteria

### Must Have

- ✅ Lists all tracked venvs from cache
- ✅ Validates each mapping against filesystem
- ✅ Table output with PROJECT, VENV, STATUS columns
- ✅ Status icons and colors (✓/✗/⚠/❌)
- ✅ `--json` outputs structured JSON
- ✅ `--orphan-only` filters orphaned venvs
- ✅ `--valid-only` filters valid venvs
- ✅ `--invalid-only` filters invalid venvs
- ✅ Empty state shows helpful message
- ✅ Summary shows counts by status
- ✅ Error on conflicting filter flags

### Should Have

- ✅ Truncate long paths with ellipsis
- ✅ Sort results alphabetically by project
- ✅ Verbose mode shows validation details
- ✅ Handle corrupted cache gracefully

### Nice to Have

- `--sort` option (by name, date, status)
- `--format` option (table, compact, detailed)
- Show disk space usage per venv

## Example Usage

### Basic List
```bash
$ prime-uve list
PROJECT                    VENV                         STATUS
────────────────────────────────────────────────────────────────
/path/to/my-app            ${HOME}/venvs/my-app_a1b2    ✓ Valid
/path/to/old-app           ${HOME}/venvs/old-app_c3d4   ✗ Orphaned

Total: 2 | Valid: 1 | Orphaned: 1 | Mismatch: 0 | Error: 0
```

### Filter Orphaned
```bash
$ prime-uve list --orphan-only
PROJECT                    VENV                         STATUS
────────────────────────────────────────────────────────────────
/path/to/old-app           ${HOME}/venvs/old-app_c3d4   ✗ Orphaned

Total: 1 | Valid: 0 | Orphaned: 1 | Mismatch: 0 | Error: 0
```

### JSON Output
```bash
$ prime-uve list --json | jq '.venvs[] | select(.status == "valid")'
{
  "project": "/path/to/my-app",
  "venv": "${HOME}/prime-uve/venvs/my-app_a1b2c3d4",
  "status": "valid",
  ...
}
```

## Success Metrics

- ✅ All unit tests pass (target: 8+ tests)
- ✅ 100% coverage of list command
- ✅ Lists 100+ venvs in < 2 seconds
- ✅ Table output is readable and well-formatted
- ✅ JSON output is valid and complete
- ✅ Filters work correctly

## Future Enhancements

1. **Sorting Options**: `--sort-by name|date|status`
2. **Disk Usage**: Show size of each venv
3. **Tree View**: Show nested projects
4. **Search**: `--search <pattern>` to filter by name
5. **Export**: `--export csv` for spreadsheet import

## References

- Architecture Design: `_todo/pending/architecture-design.md` (Section 6.2)
- Task 1.2: Cache System (validation logic)

## Notes

- This command is read-only, no side effects
- Validation can be slow for many venvs (filesystem I/O)
- Consider caching validation results (update on init/prune)
