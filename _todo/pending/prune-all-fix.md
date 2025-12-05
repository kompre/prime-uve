# Proposal: Fix `prune --all` to Include Orphaned Venvs

## Original Objective

Fix bug where `prime-uve prune --all` doesn't eliminate orphaned venvs. Restructure prune modes:
- Add new `--valid` option to delete only valid (non-orphaned) venvs
- Change `--all` to be equivalent to `--orphan + --valid` (delete everything)

## Problem Analysis

### Current Behavior

`prime-uve prune` has four modes:

1. **`--all`**: Removes all venvs tracked in cache
2. **`--orphan`**: Removes only orphaned venvs (cache mismatch or untracked)
3. **`--current`**: Removes venv for current project
4. **`<path>`**: Removes specific venv by path

### The Bug

**`--all` mode logic** (simplified):
```python
def prune_all(...):
    cache_entries = cache.list_all()
    for project_path, entry in cache_entries.items():
        venv_path = expand(entry["venv_path"])
        remove_venv_directory(venv_path)
    cache.clear()
```

**What's missing**: Untracked venvs on disk that aren't in cache won't be deleted.

**Example scenario**:
1. User manually deletes cache file: `rm ~/.prime-uve/cache.json`
2. Venvs still exist in `~/.prime-uve/venvs/`
3. User runs `prime-uve prune --all`
4. **Expected**: All venvs deleted
5. **Actual**: Nothing deleted (cache is empty, so loop doesn't run)

### Why This Happens

`--all` only operates on cache entries. It assumes cache is complete. But cache can become stale:
- User deletes cache file
- User manually creates venvs outside prime-uve
- Cache corruption

### Current `--orphan` Mode

The `--orphan` mode **does** handle untracked venvs correctly:
```python
def prune_orphan(...):
    # 1. Find orphaned cache entries
    for project_path, entry in cache_entries.items():
        if is_orphaned(project_path, entry):
            remove_venv_directory(venv_path)
            cache.remove_mapping(project_path)

    # 2. Find untracked venvs on disk
    untracked = find_untracked_venvs(cache_entries)
    for untracked_venv in untracked:
        remove_venv_directory(untracked_venv["venv_path_expanded"])
```

This is the correct approach: check both cache AND disk.

## Proposed Solution

### 1. New `--valid` Mode

Add a new mode that removes only **valid** (non-orphaned) venvs:

```python
def prune_valid(...):
    """Remove only valid venvs (cache matches .env.uve)."""
    cache_entries = cache.list_all()

    for project_path, entry in cache_entries.items():
        if not is_orphaned(project_path, entry):
            # This is valid - delete it
            venv_path = expand(entry["venv_path"])
            remove_venv_directory(venv_path)
            cache.remove_mapping(project_path)

    # Don't touch untracked venvs (they're orphans by definition)
```

**Use case**: "I want to clean up my working projects but keep orphaned venvs for inspection."

### 2. Fix `--all` Mode

Change `--all` to truly delete **everything**:

```python
def prune_all(...):
    """Remove ALL venvs - both cached and untracked."""
    # 1. Remove all cached venvs
    cache_entries = cache.list_all()
    for project_path, entry in cache_entries.items():
        venv_path = expand(entry["venv_path"])
        remove_venv_directory(venv_path)

    # 2. Clear cache
    cache.clear()

    # 3. Scan disk and remove ANY remaining venvs
    all_venvs_on_disk = scan_venv_directory()
    for venv_dir in all_venvs_on_disk:
        remove_venv_directory(venv_dir)
```

This ensures `--all` lives up to its name: **delete everything**.

### 3. Logical Equivalence

After this change:
- `--all` ≈ `--valid` + `--orphan` (delete everything)
- `--valid` = delete non-orphaned only
- `--orphan` = delete orphaned only (existing behavior)

### 4. Mode Validation

Update the mode validation to allow `--valid`:

```python
# Current validation (stays the same)
modes = [all, orphan, current, path is not None]
if sum(modes) == 0:
    raise ValueError("Must specify one mode...")
if sum(modes) > 1:
    raise ValueError("Cannot specify multiple modes...")
```

Add `--valid` to the modes list:
```python
modes = [all, orphan, valid, current, path is not None]
```

## Implementation Plan

### Step 1: Add `--valid` Flag

**File**: `src/prime_uve/cli/prune.py`

Add the option:
```python
@click.command()
@click.option("--all", "all_mode", is_flag=True, help="Remove all venvs (tracked and untracked)")
@click.option("--orphan", is_flag=True, help="Remove only orphaned venvs")
@click.option("--valid", is_flag=True, help="Remove only valid (non-orphaned) venvs")
@click.option("--current", is_flag=True, help="Remove venv for current project")
@click.argument("path", required=False)
@common_options
def prune(ctx, all_mode, orphan, valid, current, path, ...):
    # Update mode validation
    modes = [all_mode, orphan, valid, current, path is not None]
    ...
```

### Step 2: Implement `prune_valid()` Function

**File**: `src/prime_uve/cli/prune.py`

```python
def prune_valid(
    cache: Cache,
    verbose: bool,
    yes: bool,
    dry_run: bool,
    json_output: bool,
) -> None:
    """Remove only valid (non-orphaned) venvs.

    A venv is "valid" if:
    - It's in the cache
    - The project directory exists
    - The .env.uve file exists and matches cache

    Args:
        cache: Cache instance
        verbose: Show detailed output
        yes: Skip confirmation
        dry_run: Don't actually remove anything
        json_output: Output results as JSON
    """
    cache_entries = cache.list_all()

    if not cache_entries:
        if json_output:
            print_json({"removed": [], "failed": []})
        else:
            info("No managed venvs found in cache")
        return

    # Find valid venvs
    valid_venvs = []
    for project_path, entry in cache_entries.items():
        if not is_orphaned(project_path, entry):
            venv_path_expanded = expand_path_variables(entry["venv_path"])
            disk_usage = get_disk_usage(venv_path_expanded)
            valid_venvs.append({
                "project_path": project_path,
                "project_name": entry["project_name"],
                "venv_path": entry["venv_path"],
                "venv_path_expanded": venv_path_expanded,
                "disk_usage": disk_usage,
            })

    if not valid_venvs:
        if json_output:
            print_json({"removed": [], "failed": []})
        else:
            info("No valid venvs found")
        return

    # Show what will be removed
    total_size = sum(v["disk_usage"] for v in valid_venvs)

    if not json_output:
        warning(f"Will remove {len(valid_venvs)} valid venv(s)")
        warning(f"Total disk space to free: {format_bytes(total_size)}")
        echo("")
        for v in valid_venvs:
            echo(f"  • {v['project_name']}")
            if verbose:
                echo(f"    Project: {v['project_path']}")
                echo(f"    Venv:    {v['venv_path_expanded']}")
                echo(f"    Size:    {format_bytes(v['disk_usage'])}")
        echo("")

    # Confirm
    if not dry_run:
        if not confirm("Remove these valid venvs?", default=False, yes_flag=yes):
            info("Aborted")
            return

    if dry_run:
        echo("[DRY RUN] Would remove valid venvs")
        return

    # Remove venvs
    removed = []
    failed = []

    for v in valid_venvs:
        success, error = remove_venv_directory(str(v["venv_path_expanded"]), dry_run=False)
        if success:
            cache.remove_mapping(v["project_path"])
            removed.append(v["project_name"])
        else:
            failed.append({"project": v["project_name"], "error": error})

    # Output results
    if json_output:
        print_json({"removed": removed, "failed": failed})
    else:
        if removed:
            success(f"Removed {len(removed)} valid venv(s)")
            success(f"Freed {format_bytes(total_size)} disk space")
        if failed:
            error(f"Failed to remove {len(failed)} venv(s)")
```

### Step 3: Fix `prune_all()` Function

**File**: `src/prime_uve/cli/prune.py`

Update the existing `prune_all()` to also remove untracked venvs:

```python
def prune_all(...):
    """Remove ALL venvs - both cached and untracked."""
    cache_entries = cache.list_all()

    # Get all venvs: cached + untracked
    all_venvs = []

    # 1. Add cached venvs
    for project_path, entry in cache_entries.items():
        venv_path_expanded = expand_path_variables(entry["venv_path"])
        disk_usage = get_disk_usage(venv_path_expanded)
        all_venvs.append({
            "project_name": entry["project_name"],
            "venv_path_expanded": venv_path_expanded,
            "disk_usage": disk_usage,
            "tracked": True,
        })

    # 2. Add untracked venvs
    untracked = find_untracked_venvs(cache_entries)
    for u in untracked:
        all_venvs.append({
            "project_name": u["project_name"],
            "venv_path_expanded": u["venv_path_expanded"],
            "disk_usage": u["size"],
            "tracked": False,
        })

    if not all_venvs:
        if json_output:
            print_json({"removed": [], "failed": [], "freed_bytes": 0})
        else:
            info("No managed venvs found")
        return

    # Show summary
    total_size = sum(v["disk_usage"] for v in all_venvs)

    if not json_output:
        warning(f"Will remove ALL {len(all_venvs)} venv(s)")
        warning(f"Total disk space to free: {format_bytes(total_size)}")
        echo("")
        for v in all_venvs:
            tracked_marker = "" if v["tracked"] else " [untracked]"
            echo(f"  • {v['project_name']}{tracked_marker}")
            if verbose:
                echo(f"    Venv: {v['venv_path_expanded']}")
                echo(f"    Size: {format_bytes(v['disk_usage'])}")
        echo("")

    # Confirm - ALWAYS require confirmation for --all, even with --yes
    if not dry_run:
        # Override --yes flag for safety
        echo("")
        warning("⚠️  DANGER: This will delete EVERYTHING")
        echo("")
        typed_confirmation = click.prompt(
            'Type "yes" to confirm deletion of ALL venvs',
            type=str,
            default="",
        )
        if typed_confirmation.lower() != "yes":
            info("Aborted")
            return

    if dry_run:
        echo("[DRY RUN] Would remove all venvs and clear cache")
        return

    # Remove all venvs
    removed = []
    failed = []

    for v in all_venvs:
        success, error = remove_venv_directory(str(v["venv_path_expanded"]), dry_run=False)
        if success:
            removed.append(v["project_name"])
        else:
            failed.append({"project": v["project_name"], "error": error})

    # Clear cache
    cache.clear()

    # Output results
    if json_output:
        print_json({
            "removed": removed,
            "failed": failed,
            "freed_bytes": total_size,
        })
    else:
        if removed:
            success(f"Removed {len(removed)} venv(s)")
            success(f"Freed {format_bytes(total_size)} disk space")
            success("Cleared cache")
        if failed:
            error(f"Failed to remove {len(failed)} venv(s)")
```

### Step 4: Update Help Text

Update command help to clarify the new behavior:

```python
@click.option("--all", "all_mode", is_flag=True,
              help="Remove ALL venvs (both tracked and untracked)")
@click.option("--orphan", is_flag=True,
              help="Remove only orphaned venvs (cache mismatch or untracked)")
@click.option("--valid", is_flag=True,
              help="Remove only valid venvs (cache matches .env.uve)")
```

### Step 5: Update Tests

**File**: `tests/test_cli/test_prune.py`

Add tests for:
1. `--valid` mode removes only valid venvs
2. `--valid` mode leaves orphaned venvs untouched
3. `--all` mode removes tracked venvs
4. `--all` mode removes untracked venvs
5. `--all` mode works when cache is empty but venvs exist
6. Mode validation rejects `--all --valid` combination

Example test:
```python
def test_prune_all_removes_untracked_venvs(runner, tmp_path, monkeypatch):
    """Test that --all removes untracked venvs on disk."""
    # Setup: empty cache but venv exists on disk
    cache_file = tmp_path / ".prime-uve" / "cache.json"
    cache_file.parent.mkdir(exist_ok=True)
    cache_file.write_text('{"version": "1.0", "venvs": {}}')  # Empty cache

    # Create untracked venv on disk
    venv_base = tmp_path / ".prime-uve" / "venvs"
    venv_base.mkdir(parents=True)
    untracked_venv = venv_base / "test-project_abc123"
    untracked_venv.mkdir()
    (untracked_venv / "test.txt").write_text("test")

    with patch("prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file):
        with patch("prime_uve.cli.prune.get_venv_base_dir", return_value=venv_base):
            result = runner.invoke(cli, ["prune", "--all", "--yes"])

    assert result.exit_code == 0
    assert not untracked_venv.exists()  # Should be deleted
```

## Help Text Examples

### Before
```bash
$ prime-uve prune --help
Options:
  --all       Remove all managed venvs
  --orphan    Remove only orphaned venvs
  --current   Remove venv for current project
```

### After
```bash
$ prime-uve prune --help
Options:
  --all       Remove ALL venvs (tracked and untracked)
  --valid     Remove only valid venvs (cache matches .env.uve)
  --orphan    Remove only orphaned venvs (cache mismatch or untracked)
  --current   Remove venv for current project
```

## Output Examples

### `--all` (New Behavior)
```bash
$ prime-uve prune --all
⚠ Will remove ALL 3 venv(s)
⚠ Total disk space to free: 125.5 MB

  • prime-uve
  • test-project [untracked]
  • old-project

Remove ALL venvs? This cannot be undone. [y/N]: y

✓ Removed 3 venv(s)
✓ Freed 125.5 MB disk space
✓ Cleared cache
```

### `--valid` (New Mode)
```bash
$ prime-uve prune --valid
⚠ Will remove 2 valid venv(s)
⚠ Total disk space to free: 98.2 MB

  • prime-uve
  • test-project

Remove these valid venvs? [y/N]: y

✓ Removed 2 valid venv(s)
✓ Freed 98.2 MB disk space
```

## Edge Cases

1. **Empty cache + no venvs on disk**: Info message "No managed venvs found"
2. **Empty cache + untracked venvs**: `--all` removes them, `--valid` does nothing
3. **All venvs are orphaned**: `--valid` does nothing, `--all` removes them
4. **Permission denied on venv removal**: Report failure, continue with others
5. **Venv deleted between scan and removal**: Handle gracefully (no error)

## Breaking Changes

**Potentially breaking**: `--all` now removes more than before (includes untracked venvs).

**Mitigation**:
- Clear documentation in help text
- Confirmation prompt explicitly says "ALL venvs"
- Dry run mode shows what would be removed

## Alternative Approaches

### Alternative: Keep `--all` As-Is
- Add `--really-all` for everything
- **Problem**: Confusing naming, `--all` doesn't mean "all"

### Alternative: Make `--all` Require Confirmation
- Make `--all` **always** prompt, even with `--yes`
- Require `--force` for no prompt
- **Problem**: Inconsistent with other commands

### Alternative: Separate Tracked/Untracked Modes
- `--all-tracked` / `--all-untracked`
- **Problem**: Too many modes, more confusing

**Decision**: Proposed solution is simplest and most intuitive.

## Testing Strategy

1. **Unit tests**: `prune_valid()` logic, mode validation
2. **Integration tests**: Full prune workflows
3. **Edge case tests**: Empty cache, untracked venvs, permission errors
4. **Regression tests**: Ensure `--orphan` and `--current` still work

## Success Criteria

1. ✓ `prime-uve prune --all` removes ALL venvs (tracked + untracked)
2. ✓ `prime-uve prune --valid` removes only valid venvs
3. ✓ `prime-uve prune --orphan` continues to work (no regression)
4. ✓ Mode validation prevents invalid combinations
5. ✓ Help text clearly explains each mode

## User Decisions (APPROVED)

1. **Naming**: `--valid` confirmed ✓

2. **Confirmation prompt**: `--all` must ALWAYS require confirmation, even with `--yes` flag ✓
   - Requires special handling to override `--yes` behavior
   - Add explicit prompt: "This will delete EVERYTHING. Type 'yes' to confirm:"

3. **Cache clearing**: `--valid` MUST also clear cache entries for removed venvs ✓
   - Updated implementation in Step 2

4. **Untracked venvs in `--valid`**: Correctly ignores them (they're orphans) ✓

5. **Disk scan performance**: No `--skip-disk-scan` flag needed ✓

---

## PROPOSAL APPROVED - Ready for Implementation

**Approved by**: User
**Approval date**: 2025-12-05
**Status**: ✅ IMPLEMENTATION COMPLETE

---

## Implementation Summary

**Implementation date**: 2025-12-05
**Implemented by**: Haiku agent

### Changes Made

1. **src/prime_uve/cli/main.py**
   - ✅ Added `--valid` flag to prune command
   - ✅ Updated help text for all prune modes
   - ✅ Updated mode validation

2. **src/prime_uve/cli/prune.py**
   - ✅ Implemented `prune_valid()` function
     - Removes only valid venvs (cache matches .env.uve)
     - Clears cache entries for removed venvs
     - Respects `--yes` flag for confirmation
   - ✅ Fixed `prune_all()` function
     - Removes both cached AND untracked venvs
     - Uses typed confirmation with `click.prompt()`
     - Overrides `--yes` flag (always requires explicit "yes" input)
     - Shows tracked vs untracked venvs in output
   - ✅ Updated mode validation to include `valid` flag

3. **tests/test_cli/test_prune.py**
   - ✅ Added `TestPruneValid` class with 5 comprehensive tests
   - ✅ Enhanced `TestPruneAll` with 4 new tests for untracked venvs
   - ✅ Added mode validation tests for invalid combinations
   - ✅ All 410 tests passing (39 in test_prune.py)

### Test Results

```
410 tests passed (8 skipped)
- test_prune_valid_empty_cache ✅
- test_prune_valid_removes_only_valid_venvs ✅
- test_prune_valid_clears_cache_entries ✅
- test_prune_valid_respects_yes_flag ✅
- test_prune_valid_dry_run ✅
- test_prune_all_removes_untracked_venvs ✅
- test_prune_all_requires_typed_confirmation ✅
- test_prune_all_dry_run ✅
- test_prune_command_all_valid_combination ✅
- test_prune_command_valid_orphan_combination ✅
```

### Ready for Review and Commit

All requirements met. Ready for user review and git commit.