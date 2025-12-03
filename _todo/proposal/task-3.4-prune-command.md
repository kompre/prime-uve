# Task 3.4: Implement `prime-uve prune`

**Phase**: 3 (CLI Commands)
**Priority**: High (essential for cleanup)
**Estimated Complexity**: High
**Status**: Proposal

## Objective

Implement the `prime-uve prune` command to clean up venv directories and cache entries. Supports multiple modes: pruning all venvs, orphaned venvs only, current project, or specific paths.

## Dependencies

**Requires**:
- Task 1.2: Cache System ✅
- Task 1.3: .env.uve File Management ✅
- Task 1.4: Project Detection ✅
- Task 3.1: CLI Framework Setup ⏳

**Blocks**:
- None (independent of other commands)

## Background

`prime-uve prune` provides safe cleanup of venv directories and cache entries. Over time, users may:
- Delete projects but leave venvs behind
- Manually change .env.uve paths
- Accumulate test venvs
- Need to reclaim disk space

The command must be:
- **Safe**: Confirm before deleting (unless --yes)
- **Transparent**: Show what will be deleted
- **Atomic**: Update cache and filesystem together
- **Reversible**: Support --dry-run

## Requirements

### Functional Requirements

1. **Four Pruning Modes**:

   **a) `prune --all`**: Remove all tracked venvs
   - Delete all venv directories
   - Clear entire cache
   - Require confirmation (or --yes)
   - Show total space reclaimed

   **b) `prune --orphan`**: Remove orphaned venvs only
   - Run validation on all cached venvs
   - Delete venvs where:
     - Project directory doesn't exist, OR
     - .env.uve missing/doesn't match cache
   - Keep valid venvs untouched
   - Remove from cache

   **c) `prune --current`**: Remove current project's venv
   - Find current project root
   - Get venv from cache
   - Delete venv directory
   - Remove from cache
   - Optionally clear .env.uve

   **d) `prune <path>`**: Remove specific venv by path
   - Validate path is within prime-uve directory
   - Delete venv directory
   - Remove from cache if tracked
   - Error if path is outside managed directory

2. **Safety Features**:
   - `--yes` / `-y`: Skip confirmation prompts
   - `--dry-run`: Show what would be deleted without deleting
   - Confirmation prompt shows paths and sizes
   - Prevent accidental deletion of active venvs

3. **Validation Before Deletion**:
   - Check if venv is in use (activated shell)
   - Warn if deleting current project venv
   - Validate paths before deletion

4. **Output**:
   - List what will be deleted
   - Show disk space to be reclaimed
   - Progress indicator for multiple venvs
   - Summary of deletions

### Non-Functional Requirements

- **Safety**: No data loss, clear confirmations
- **Performance**: Delete 100+ venvs efficiently
- **Atomicity**: Cache and filesystem stay in sync
- **Idempotency**: Safe to run multiple times

## Implementation Plan

### 1. Command Structure

```python
# src/prime_uve/cli/prune.py
"""prime-uve prune command."""
import click
import shutil
from pathlib import Path

from prime_uve.cli import output, errors, options
from prime_uve.core.cache import Cache
from prime_uve.core.paths import expand_path_variables
from prime_uve.core.project import find_project_root
from prime_uve.core.env_file import find_env_file, write_env_file


@click.command()
@click.option("--all", "prune_all", is_flag=True, help="Remove all venvs")
@click.option("--orphan", is_flag=True, help="Remove orphaned venvs only")
@click.option("--current", is_flag=True, help="Remove current project's venv")
@click.option("--clear-env", is_flag=True, help="Also clear .env.uve (with --current)")
@click.argument("path", type=click.Path(exists=True), required=False)
@options.common_options
@click.pass_context
def prune(
    ctx: click.Context,
    prune_all: bool,
    orphan: bool,
    current: bool,
    clear_env: bool,
    path: str | None,
    yes: bool,
    dry_run: bool
) -> None:
    """Clean up venv directories and cache entries.

    Modes (mutually exclusive):
        --all       Remove all tracked venvs
        --orphan    Remove orphaned venvs only
        --current   Remove current project's venv
        <path>      Remove specific venv by path

    Safety options:
        --yes       Skip confirmation prompts
        --dry-run   Show what would be deleted without deleting

    Examples:
        prime-uve prune --orphan        Clean up deleted projects
        prime-uve prune --current       Remove venv for current project
        prime-uve prune --all --yes     Remove all venvs (no prompt)
        prime-uve prune /path/to/venv   Remove specific venv
    """
    verbose = ctx.obj.get("verbose", False)

    try:
        # Validate mutually exclusive options
        mode_count = sum([prune_all, orphan, current, bool(path)])
        if mode_count == 0:
            raise errors.UserError(
                "Must specify a pruning mode",
                hint="Use --all, --orphan, --current, or provide a path"
            )
        if mode_count > 1:
            raise errors.UserError(
                "Cannot combine pruning modes",
                hint="Use only one of: --all, --orphan, --current, or path"
            )

        # Validate --clear-env only with --current
        if clear_env and not current:
            raise errors.UserError(
                "--clear-env can only be used with --current",
                hint="Remove --clear-env or add --current"
            )

        # Execute appropriate mode
        if prune_all:
            _prune_all(verbose, yes, dry_run)
        elif orphan:
            _prune_orphan(verbose, yes, dry_run)
        elif current:
            _prune_current(verbose, yes, dry_run, clear_env)
        elif path:
            _prune_path(Path(path), verbose, yes, dry_run)

    except errors.CliError:
        raise
    except Exception as e:
        errors.handle_error(e, verbose)


def _prune_all(verbose: bool, yes: bool, dry_run: bool) -> None:
    """Remove all tracked venvs."""
    cache = Cache()
    mappings = cache.list_all()

    if not mappings:
        output.info("No venvs to prune")
        return

    # Calculate total size
    total_size = 0
    venvs_to_delete = []

    for project_path in mappings:
        venv_path = expand_path_variables(mappings[project_path]["venv_path"])
        if venv_path.exists():
            size = _get_dir_size(venv_path)
            total_size += size
            venvs_to_delete.append((project_path, venv_path, size))

    # Show what will be deleted
    output.warning(f"This will delete {len(venvs_to_delete)} venv(s)")
    for project, venv, size in venvs_to_delete:
        output.info(f"  {project}")
        output.info(f"    → {venv} ({_format_size(size)})")

    output.warning(f"Total space to reclaim: {_format_size(total_size)}")

    if dry_run:
        output.info("Dry run - no changes made")
        return

    # Confirm
    if not yes:
        if not click.confirm("Proceed with deletion?"):
            output.info("Aborted")
            return

    # Delete
    deleted = 0
    for project, venv, _ in venvs_to_delete:
        output.verbose(f"Deleting {venv}...")
        try:
            shutil.rmtree(venv)
            deleted += 1
            output.success(f"Deleted {venv}")
        except Exception as e:
            output.error(f"Failed to delete {venv}: {e}")

    # Clear cache
    cache.clear()
    output.success(f"Deleted {deleted} venv(s), cleared cache")
    output.info(f"Reclaimed {_format_size(total_size)}")


def _prune_orphan(verbose: bool, yes: bool, dry_run: bool) -> None:
    """Remove orphaned venvs only."""
    cache = Cache()
    mappings = cache.list_all()

    if not mappings:
        output.info("No venvs to prune")
        return

    # Find orphaned venvs
    orphaned = []
    for project_path in mappings:
        validation = cache.validate_mapping(Path(project_path))
        if validation.status.value in ["orphaned", "mismatch"]:
            venv_path = expand_path_variables(mappings[project_path]["venv_path"])
            if venv_path.exists():
                size = _get_dir_size(venv_path)
                orphaned.append({
                    "project": project_path,
                    "venv": venv_path,
                    "size": size,
                    "reason": validation.message or validation.status.value
                })

    if not orphaned:
        output.info("No orphaned venvs found")
        return

    # Show what will be deleted
    total_size = sum(o["size"] for o in orphaned)
    output.warning(f"Found {len(orphaned)} orphaned venv(s)")

    for o in orphaned:
        output.info(f"  {o['project']}")
        output.info(f"    → {o['venv']} ({_format_size(o['size'])})")
        output.info(f"    Reason: {o['reason']}")

    output.warning(f"Total space to reclaim: {_format_size(total_size)}")

    if dry_run:
        output.info("Dry run - no changes made")
        return

    # Confirm
    if not yes:
        if not click.confirm("Proceed with deletion?"):
            output.info("Aborted")
            return

    # Delete
    deleted = 0
    for o in orphaned:
        output.verbose(f"Deleting {o['venv']}...")
        try:
            shutil.rmtree(o["venv"])
            cache.remove_mapping(Path(o["project"]))
            deleted += 1
            output.success(f"Deleted {o['venv']}")
        except Exception as e:
            output.error(f"Failed to delete {o['venv']}: {e}")

    output.success(f"Deleted {deleted} orphaned venv(s)")
    output.info(f"Reclaimed {_format_size(total_size)}")


def _prune_current(verbose: bool, yes: bool, dry_run: bool, clear_env: bool) -> None:
    """Remove current project's venv."""
    # Find project root
    project_root = find_project_root()
    if not project_root:
        raise errors.UserError(
            "Not in a Python project",
            hint="Navigate to a project directory"
        )

    # Get venv from cache
    cache = Cache()
    mapping = cache.get_mapping(project_root)
    if not mapping:
        raise errors.UserError(
            "Current project not initialized with prime-uve",
            hint="Run 'prime-uve init' first"
        )

    venv_path = expand_path_variables(mapping["venv_path"])

    # Calculate size
    size = _get_dir_size(venv_path) if venv_path.exists() else 0

    # Show what will be deleted
    output.warning(f"This will delete the venv for {project_root.name}")
    output.info(f"  Project: {project_root}")
    output.info(f"  Venv: {venv_path}")
    output.info(f"  Size: {_format_size(size)}")

    if clear_env:
        output.info(f"  Will also clear .env.uve")

    if dry_run:
        output.info("Dry run - no changes made")
        return

    # Confirm
    if not yes:
        if not click.confirm("Proceed with deletion?"):
            output.info("Aborted")
            return

    # Delete
    if venv_path.exists():
        shutil.rmtree(venv_path)
        output.success(f"Deleted {venv_path}")

    # Remove from cache
    cache.remove_mapping(project_root)
    output.success("Removed from cache")

    # Clear .env.uve if requested
    if clear_env:
        env_file = find_env_file(project_root)
        if env_file.exists():
            env_file.unlink()
            output.success("Cleared .env.uve")

    output.info(f"Reclaimed {_format_size(size)}")


def _prune_path(path: Path, verbose: bool, yes: bool, dry_run: bool) -> None:
    """Remove specific venv by path."""
    # Validate path is within prime-uve directory
    # (Prevent accidental deletion of random directories)
    home = Path.home()
    prime_uve_dir = home / "prime-uve" / "venvs"

    if not path.is_relative_to(prime_uve_dir):
        raise errors.UserError(
            f"Path is outside prime-uve directory: {path}",
            hint=f"Only venvs under {prime_uve_dir} can be pruned"
        )

    if not path.exists():
        raise errors.UserError(f"Path does not exist: {path}")

    # Calculate size
    size = _get_dir_size(path)

    # Check if tracked in cache
    cache = Cache()
    tracked_project = None
    for project_path in cache.list_all():
        mapping = cache.get_mapping(Path(project_path))
        if expand_path_variables(mapping["venv_path"]) == path:
            tracked_project = project_path
            break

    # Show what will be deleted
    output.warning(f"This will delete: {path}")
    output.info(f"  Size: {_format_size(size)}")
    if tracked_project:
        output.info(f"  Tracked project: {tracked_project}")
    else:
        output.warning("  Not tracked in cache")

    if dry_run:
        output.info("Dry run - no changes made")
        return

    # Confirm
    if not yes:
        if not click.confirm("Proceed with deletion?"):
            output.info("Aborted")
            return

    # Delete
    shutil.rmtree(path)
    output.success(f"Deleted {path}")

    # Remove from cache if tracked
    if tracked_project:
        cache.remove_mapping(Path(tracked_project))
        output.success("Removed from cache")

    output.info(f"Reclaimed {_format_size(size)}")


def _get_dir_size(path: Path) -> int:
    """Calculate directory size in bytes."""
    total = 0
    try:
        for entry in path.rglob("*"):
            if entry.is_file():
                total += entry.stat().st_size
    except (PermissionError, OSError):
        pass  # Skip inaccessible files
    return total


def _format_size(bytes: int) -> str:
    """Format bytes as human-readable size."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes < 1024.0:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.1f} PB"
```

### 2. Testing

```python
# tests/cli/test_prune.py
"""Test prime-uve prune command."""
import pytest
import shutil
from pathlib import Path

from prime_uve.cli.main import cli
from prime_uve.core.cache import Cache


def test_prune_no_mode(isolated_cli):
    """Test error when no mode specified."""
    result = isolated_cli.invoke(cli, ["prune"])
    assert result.exit_code == 1
    assert "Must specify a pruning mode" in result.output


def test_prune_conflicting_modes(isolated_cli):
    """Test error with conflicting modes."""
    result = isolated_cli.invoke(cli, ["prune", "--all", "--orphan"])
    assert result.exit_code == 1
    assert "Cannot combine" in result.output


def test_prune_orphan_dry_run(isolated_cli, tmp_path):
    """Test --orphan with --dry-run."""
    # Setup orphaned venv
    cache = Cache()
    cache.add_mapping(
        tmp_path / "deleted-project",
        "${HOME}/venvs/test",
        "test"
    )

    result = isolated_cli.invoke(cli, ["prune", "--orphan", "--dry-run"])
    assert result.exit_code == 0
    assert "Dry run" in result.output
    assert "deleted-project" in result.output


def test_prune_current(isolated_cli, tmp_path):
    """Test --current mode."""
    # Setup current project
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text('[project]\nname="test"')

    venv = tmp_path / "venvs" / "test"
    venv.mkdir(parents=True)

    cache = Cache()
    cache.add_mapping(project, "${HOME}/venvs/test", "test")

    # Test
    result = isolated_cli.invoke(
        cli,
        ["prune", "--current", "--yes"],
        input="y\n"
    )
    assert result.exit_code == 0
    assert not venv.exists()


def test_prune_path_validation(isolated_cli, tmp_path):
    """Test path validation (outside prime-uve dir)."""
    random_dir = tmp_path / "random"
    random_dir.mkdir()

    result = isolated_cli.invoke(cli, ["prune", str(random_dir)])
    assert result.exit_code == 1
    assert "outside prime-uve directory" in result.output


def test_prune_all_with_yes(isolated_cli, tmp_path):
    """Test --all with --yes flag."""
    # Setup venvs
    cache = Cache()
    venv1 = tmp_path / "venvs" / "test1"
    venv1.mkdir(parents=True)
    cache.add_mapping(tmp_path / "proj1", "${HOME}/venvs/test1", "test1")

    result = isolated_cli.invoke(cli, ["prune", "--all", "--yes"])
    assert result.exit_code == 0
    assert not venv1.exists()
    assert len(cache.list_all()) == 0
```

## Acceptance Criteria

### Must Have

- ✅ Four pruning modes work correctly (--all, --orphan, --current, path)
- ✅ `--yes` skips confirmation prompts
- ✅ `--dry-run` shows actions without executing
- ✅ Shows paths and sizes before deletion
- ✅ Updates cache and filesystem atomically
- ✅ Error on conflicting modes
- ✅ Validates paths are within prime-uve directory
- ✅ Shows space reclaimed
- ✅ Clear error messages

### Should Have

- ✅ `--clear-env` option with --current
- ✅ Warns if deleting current project venv
- ✅ Progress indicator for multiple deletions
- ✅ Handles permission errors gracefully
- ✅ Summary output with statistics

### Nice to Have

- Backup before deletion (optional)
- Undo last prune operation
- Interactive selection (checkbox list)

## Success Metrics

- ✅ All unit tests pass (target: 12+ tests)
- ✅ 100% coverage of prune command
- ✅ Safe (no accidental deletions)
- ✅ Efficient (deletes 100+ venvs quickly)
- ✅ Clear confirmations and output

## Future Enhancements

1. **Interactive Mode**: Select venvs to prune with checkboxes
2. **Backup**: `--backup` to create archive before deletion
3. **Undo**: `prime-uve prune --undo` to restore last pruned venvs
4. **Age Filter**: `--older-than 30d` to prune old venvs
5. **Size Filter**: `--larger-than 1GB` to prune large venvs

## References

- Architecture Design: `_todo/pending/architecture-design.md` (Section 6.3)
- Task 1.2: Cache System (validation, removal)

## Notes

- This is a destructive operation - safety is paramount
- Always show what will be deleted before deleting
- Consider adding confirmation even with --yes for --all
- Disk usage calculation can be slow for large venvs
