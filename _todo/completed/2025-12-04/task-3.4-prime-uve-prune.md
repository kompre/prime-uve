# Task 3.4: Implement `prime-uve prune`

## Objective

Implement the `prime-uve prune` command to clean up venv directories. This command provides safe, controlled deletion of venvs with multiple modes: all, orphan, current project, or specific path.

## Context

Venvs consume significant disk space. Users need a safe way to clean up:
- Orphaned venvs (project deleted/moved)
- Current project's venv (for fresh start)
- All venvs (clean slate)
- Specific venv by path

Safety is critical - accidental deletion could lose work.

## Dependencies

**Required (all complete):**
- Task 1.2: Cache system ✅
- Task 1.3: .env.uve management ✅
- Task 3.1: CLI framework ✅

**Strongly recommended:**
- Task 3.2: `prime-uve init` - Creates venvs to prune
- Task 3.3: `prime-uve list` - Provides validation logic to reuse

## Deliverables

### 1. Implementation Files

**`src/prime_uve/cli/prune.py`** (~300-350 lines)
- Main `prune` command with 4 modes
- Confirmation prompts with detailed preview
- Dry-run support
- Progress indicators for bulk deletions
- Statistics summary (deleted count, freed space)

**Modes:**
1. `prune --all` - Remove all venvs and clear cache
2. `prune --orphan` - Remove orphaned venvs only
3. `prune --current` - Remove current project's venv
4. `prune <path>` - Remove specific venv by path

### 2. Test Suite

**`tests/test_cli/test_prune.py`** (~25-30 tests)

**Test Categories:**

1. **prune --all** (6 tests)
   - Removes all venv directories
   - Clears entire cache
   - Shows confirmation prompt
   - `--yes` skips confirmation
   - `--dry-run` shows plan without deleting
   - Empty cache handled gracefully

2. **prune --orphan** (7 tests)
   - Identifies orphaned venvs correctly
   - Removes only orphaned venvs
   - Preserves valid venvs
   - Updates cache to remove orphan entries
   - Shows confirmation with details
   - No orphans found message
   - `--dry-run` shows what would be deleted

3. **prune --current** (6 tests)
   - Finds current project's venv from cache
   - Removes venv directory
   - Removes cache entry
   - Clears .env.uve content
   - Not in a tracked project error
   - Confirmation prompt

4. **prune <path>** (6 tests)
   - Removes venv at specific path
   - Updates cache if tracked
   - Validates path is within prime-uve directory
   - Rejects dangerous paths (/, ~, etc.)
   - Path doesn't exist handled gracefully
   - Permission errors handled

5. **Safety and Edge Cases** (5 tests)
   - Cannot run multiple modes together
   - Confirmation required (unless --yes)
   - KeyboardInterrupt during deletion
   - Partial deletion failure recovery
   - Statistics accuracy (count, size)

### 3. Integration Points

**CLI Command Registration** (in `main.py`):
```python
from prime_uve.cli import prune

@cli.command()
@click.argument('path', required=False, type=click.Path())
@click.option('--all', 'prune_all', is_flag=True, help='Remove all venvs')
@click.option('--orphan', is_flag=True, help='Remove orphaned venvs only')
@click.option('--current', is_flag=True, help='Remove current project venv')
@common_options
@handle_errors
def prune_cmd(ctx, path, prune_all, orphan, current, verbose, yes, dry_run, json_output):
    """Clean up venv directories."""
    from prime_uve.cli.prune import prune_command
    prune_command(ctx, path, prune_all, orphan, current, verbose, yes, dry_run, json_output)
```

## Command Specification

### Usage

```bash
prime-uve prune [OPTIONS] [PATH]
```

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--all` | | False | Remove all venvs and clear cache |
| `--orphan` | | False | Remove only orphaned venvs |
| `--current` | | False | Remove current project's venv |
| `PATH` | | | Specific venv path to remove |
| `--verbose` | `-v` | False | Show detailed output |
| `--yes` | `-y` | False | Skip confirmation prompts |
| `--dry-run` | | False | Show what would be deleted |
| `--json` | | False | Output as JSON |

**Mutual Exclusivity:** Only one of --all, --orphan, --current, or PATH can be specified.

### Output Examples

**prune --all (confirmation):**
```
⚠ Warning: This will delete ALL managed venvs

Venvs to delete:
  • myproject         (~/prime-uve/venvs/myproj_a1b2)     125 MB
  • another-project   (~/prime-uve/venvs/anothe_c3d4)      89 MB
  • old-project       (~/prime-uve/venvs/oldpro_e5f6)     156 MB

Total: 3 venvs, 370 MB

This will also clear the entire cache.

Continue? [y/N]:
```

**prune --all (after confirmation):**
```
Removing all venvs...
  ✓ Removed myproject (125 MB freed)
  ✓ Removed another-project (89 MB freed)
  ✓ Removed old-project (156 MB freed)
✓ Cleared cache

Summary: 3 venvs removed, 370 MB freed
```

**prune --orphan:**
```
Finding orphaned venvs...

Orphaned venvs to delete:
  • old-project       (~/prime-uve/venvs/oldpro_e5f6)     156 MB
    Reason: Project directory not found

  • broken-project    (~/prime-uve/venvs/broken_g7h8)       0 B
    Reason: .env.uve path mismatch

Total: 2 orphaned venvs, 156 MB

Continue? [y/N]: y

Removing orphaned venvs...
  ✓ Removed old-project (156 MB freed)
  ✓ Removed broken-project (0 B freed)
✓ Updated cache (removed 2 entries)

Summary: 2 venvs removed, 156 MB freed
```

**prune --orphan (none found):**
```
Finding orphaned venvs...

✓ No orphaned venvs found. All venvs are valid!
```

**prune --current:**
```
Current project: myproject
Venv: ~/prime-uve/venvs/myproject_a1b2c3d4 (125 MB)

This will:
  • Delete venv directory
  • Remove cache entry
  • Clear .env.uve content

Continue? [y/N]: y

  ✓ Removed venv directory (125 MB freed)
  ✓ Removed cache entry
  ✓ Cleared .env.uve

Summary: 1 venv removed, 125 MB freed

To recreate: Run 'prime-uve init'
```

**prune <path>:**
```
Venv to delete:
  Path: /home/user/prime-uve/venvs/myproject_a1b2c3d4
  Size: 125 MB
  Tracked: Yes (project: myproject)

Continue? [y/N]: y

  ✓ Removed venv directory (125 MB freed)
  ✓ Removed cache entry

Summary: 1 venv removed, 125 MB freed
```

**prune --dry-run --all:**
```
[DRY RUN] Would delete ALL managed venvs:
  [DRY RUN] Would remove: myproject (125 MB)
  [DRY RUN] Would remove: another-project (89 MB)
  [DRY RUN] Would remove: old-project (156 MB)
[DRY RUN] Would clear cache (3 entries)

[DRY RUN] Summary: 3 venvs, 370 MB
```

**prune --json --orphan:**
```json
{
  "mode": "orphan",
  "dry_run": false,
  "deleted": [
    {
      "project_name": "old-project",
      "venv_path": "${HOME}/prime-uve/venvs/old-project_e5f6g7h8",
      "venv_path_expanded": "/home/user/prime-uve/venvs/old-project_e5f6g7h8",
      "size_bytes": 163577856,
      "reason": "project_missing"
    }
  ],
  "summary": {
    "venvs_removed": 1,
    "bytes_freed": 163577856,
    "cache_entries_removed": 1
  }
}
```

**Error (not in tracked project):**
```
✗ Error: Current project not tracked
  No .env.uve found or project not in cache.

  To initialize: Run 'prime-uve init'
  To see tracked projects: Run 'prime-uve list'
```

**Error (dangerous path):**
```
✗ Error: Dangerous path rejected
  Path must be within prime-uve venv directory.

  Provided: /home/user
  Expected: /home/user/prime-uve/venvs/*
```

## Implementation Logic

### Main Flow

```python
def prune_command(ctx, path, prune_all, orphan, current, verbose, yes, dry_run, json_output):
    # 1. Validate mutual exclusivity
    modes = sum([bool(prune_all), bool(orphan), bool(current), bool(path)])
    if modes == 0:
        raise ValueError(
            "Must specify one mode: --all, --orphan, --current, or PATH\n"
            "Run 'prime-uve prune --help' for usage"
        )
    if modes > 1:
        raise ValueError("Cannot use multiple prune modes together")

    # 2. Dispatch to mode handler
    if prune_all:
        result = prune_all_handler(verbose, yes, dry_run)
    elif orphan:
        result = prune_orphan_handler(verbose, yes, dry_run)
    elif current:
        result = prune_current_handler(verbose, yes, dry_run)
    else:
        result = prune_path_handler(path, verbose, yes, dry_run)

    # 3. Output results
    if json_output:
        output_json(result)
    else:
        output_summary(result)
```

### Mode: prune --all

```python
def prune_all_handler(verbose, yes, dry_run):
    cache = Cache()
    mappings = cache.list_all()

    if not mappings:
        info("No venvs to delete.")
        return {"venvs_removed": 0, "bytes_freed": 0}

    # Calculate total size
    venvs_to_delete = []
    total_size = 0
    for project_path, cache_entry in mappings.items():
        venv_path_expanded = expand_path_variables(cache_entry["venv_path"])
        size = get_disk_usage(venv_path_expanded) if venv_path_expanded.exists() else 0
        venvs_to_delete.append({
            "project_name": cache_entry["project_name"],
            "venv_path": cache_entry["venv_path"],
            "venv_path_expanded": venv_path_expanded,
            "size_bytes": size
        })
        total_size += size

    # Show confirmation
    if not dry_run:
        warning("This will delete ALL managed venvs")
        echo("\nVenvs to delete:")
        for venv in venvs_to_delete:
            size_str = format_bytes(venv["size_bytes"])
            echo(f"  • {venv['project_name']:<20} ({truncate_path(venv['venv_path'], 32)}) {size_str:>10}")

        echo(f"\nTotal: {len(venvs_to_delete)} venvs, {format_bytes(total_size)}")
        echo("\nThis will also clear the entire cache.")

        if not confirm("Continue?", default=False, yes_flag=yes):
            raise click.Abort()

    # Delete venvs
    deleted_count = 0
    bytes_freed = 0

    if dry_run:
        echo("[DRY RUN] Would delete ALL managed venvs:")
        for venv in venvs_to_delete:
            size_str = format_bytes(venv["size_bytes"])
            echo(f"  [DRY RUN] Would remove: {venv['project_name']} ({size_str})")
        echo(f"[DRY RUN] Would clear cache ({len(venvs_to_delete)} entries)")
    else:
        echo("\nRemoving all venvs...")
        for venv in venvs_to_delete:
            try:
                if venv["venv_path_expanded"].exists():
                    shutil.rmtree(venv["venv_path_expanded"])
                    bytes_freed += venv["size_bytes"]
                success(f"Removed {venv['project_name']} ({format_bytes(venv['size_bytes'])} freed)")
                deleted_count += 1
            except Exception as e:
                error(f"Failed to remove {venv['project_name']}: {e}")

        # Clear cache
        cache.clear_all()
        success("Cleared cache")

    return {
        "mode": "all",
        "venvs_removed": deleted_count,
        "bytes_freed": bytes_freed,
        "cache_entries_removed": deleted_count
    }
```

### Mode: prune --orphan

```python
def prune_orphan_handler(verbose, yes, dry_run):
    cache = Cache()
    mappings = cache.list_all()

    # Validate all mappings to find orphans
    echo("Finding orphaned venvs...")
    orphans = []

    for project_path, cache_entry in mappings.items():
        result = validate_project_mapping(project_path, cache_entry)
        if result.status != ValidationStatus.VALID:
            orphans.append({
                "project_name": result.project_name,
                "project_path": project_path,
                "venv_path": result.venv_path,
                "venv_path_expanded": result.venv_path_expanded,
                "size_bytes": result.disk_usage_bytes,
                "reason": result.status.name.lower()
            })

    if not orphans:
        success("No orphaned venvs found. All venvs are valid!")
        return {"venvs_removed": 0, "bytes_freed": 0}

    # Show confirmation
    total_size = sum(o["size_bytes"] for o in orphans)

    if not dry_run:
        echo("\nOrphaned venvs to delete:")
        for orphan in orphans:
            size_str = format_bytes(orphan["size_bytes"])
            reason_str = orphan["reason"].replace("_", " ").title()
            echo(f"  • {orphan['project_name']:<20} ({truncate_path(orphan['venv_path'], 32)}) {size_str:>10}")
            echo(f"    Reason: {reason_str}")

        echo(f"\nTotal: {len(orphans)} orphaned venvs, {format_bytes(total_size)}")

        if not confirm("Continue?", default=False, yes_flag=yes):
            raise click.Abort()

    # Delete orphans
    deleted_count = 0
    bytes_freed = 0

    if dry_run:
        echo("[DRY RUN] Would remove orphaned venvs:")
        for orphan in orphans:
            size_str = format_bytes(orphan["size_bytes"])
            echo(f"  [DRY RUN] Would remove: {orphan['project_name']} ({size_str})")
    else:
        echo("\nRemoving orphaned venvs...")
        for orphan in orphans:
            try:
                if orphan["venv_path_expanded"].exists():
                    shutil.rmtree(orphan["venv_path_expanded"])
                    bytes_freed += orphan["size_bytes"]
                cache.remove_mapping(orphan["project_path"])
                success(f"Removed {orphan['project_name']} ({format_bytes(orphan['size_bytes'])} freed)")
                deleted_count += 1
            except Exception as e:
                error(f"Failed to remove {orphan['project_name']}: {e}")

        success(f"Updated cache (removed {deleted_count} entries)")

    return {
        "mode": "orphan",
        "venvs_removed": deleted_count,
        "bytes_freed": bytes_freed,
        "cache_entries_removed": deleted_count,
        "deleted": orphans[:deleted_count]
    }
```

### Mode: prune --current

```python
def prune_current_handler(verbose, yes, dry_run):
    # Find project root
    project_root = find_project_root()
    if not project_root:
        raise ValueError("Not in a Python project (no pyproject.toml found)")

    # Check if tracked
    cache = Cache()
    cache_entry = cache.get_mapping(str(project_root))
    if not cache_entry:
        raise ValueError(
            "Current project not tracked\n"
            "Run 'prime-uve init' to initialize"
        )

    venv_path = cache_entry["venv_path"]
    venv_path_expanded = expand_path_variables(venv_path)
    size = get_disk_usage(venv_path_expanded) if venv_path_expanded.exists() else 0

    # Show confirmation
    if not dry_run:
        echo(f"Current project: {cache_entry['project_name']}")
        echo(f"Venv: {venv_path} ({format_bytes(size)})")
        echo("\nThis will:")
        echo("  • Delete venv directory")
        echo("  • Remove cache entry")
        echo("  • Clear .env.uve content")

        if not confirm("Continue?", default=False, yes_flag=yes):
            raise click.Abort()

    # Delete current project's venv
    if dry_run:
        echo(f"[DRY RUN] Would remove current project venv: {cache_entry['project_name']}")
        echo(f"[DRY RUN] Would free: {format_bytes(size)}")
    else:
        # Remove venv directory
        if venv_path_expanded.exists():
            shutil.rmtree(venv_path_expanded)
            success(f"Removed venv directory ({format_bytes(size)} freed)")

        # Remove cache entry
        cache.remove_mapping(str(project_root))
        success("Removed cache entry")

        # Clear .env.uve
        env_file = project_root / ".env.uve"
        if env_file.exists():
            env_file.write_text("")
            success("Cleared .env.uve")

        info("\nTo recreate: Run 'prime-uve init'")

    return {
        "mode": "current",
        "venvs_removed": 1,
        "bytes_freed": size,
        "cache_entries_removed": 1
    }
```

### Mode: prune <path>

```python
def prune_path_handler(path_str, verbose, yes, dry_run):
    path = Path(path_str).resolve()

    # Validate path safety
    venv_base = Path.home() / "prime-uve" / "venvs"
    if not is_subpath(path, venv_base):
        raise ValueError(
            f"Dangerous path rejected\n"
            f"Path must be within prime-uve venv directory.\n\n"
            f"Provided: {path}\n"
            f"Expected: {venv_base}/*"
        )

    if not path.exists():
        raise ValueError(f"Path does not exist: {path}")

    # Check if tracked
    cache = Cache()
    project_path = cache.find_by_venv_path(str(path))
    tracked = project_path is not None

    size = get_disk_usage(path)

    # Show confirmation
    if not dry_run:
        echo("Venv to delete:")
        echo(f"  Path: {path}")
        echo(f"  Size: {format_bytes(size)}")
        if tracked:
            cache_entry = cache.get_mapping(project_path)
            echo(f"  Tracked: Yes (project: {cache_entry['project_name']})")
        else:
            echo("  Tracked: No")

        if not confirm("Continue?", default=False, yes_flag=yes):
            raise click.Abort()

    # Delete
    if dry_run:
        echo(f"[DRY RUN] Would remove: {path} ({format_bytes(size)})")
        if tracked:
            echo("[DRY RUN] Would remove cache entry")
    else:
        shutil.rmtree(path)
        success(f"Removed venv directory ({format_bytes(size)} freed)")

        if tracked:
            cache.remove_mapping(project_path)
            success("Removed cache entry")

    return {
        "mode": "path",
        "venvs_removed": 1,
        "bytes_freed": size,
        "cache_entries_removed": 1 if tracked else 0
    }
```

## Acceptance Criteria

### Functional Requirements

- [ ] `--all` removes all venvs and clears cache
- [ ] `--orphan` identifies and removes only orphaned venvs
- [ ] `--current` removes current project's venv
- [ ] `<path>` removes venv at specific path
- [ ] Only one mode can be specified at a time
- [ ] Confirmation prompt shows details before deletion
- [ ] `--yes` skips confirmation
- [ ] `--dry-run` shows plan without executing
- [ ] `--json` outputs machine-readable results
- [ ] Cache updated after deletions
- [ ] `.env.uve` cleared when using `--current`
- [ ] Path validation rejects dangerous paths
- [ ] Statistics accurate (count, bytes freed)

### Safety Requirements

- [ ] ALWAYS requires confirmation unless `--yes`
- [ ] Shows exactly what will be deleted
- [ ] Validates paths before deletion
- [ ] Rejects paths outside prime-uve directory
- [ ] Handles KeyboardInterrupt gracefully
- [ ] Partial failures don't corrupt cache
- [ ] Clear error messages for all failure modes

### Non-Functional Requirements

- [ ] Performance: Deletes 10 venvs in <5 seconds
- [ ] Works cross-platform (Windows, macOS, Linux)
- [ ] Handles permission errors gracefully
- [ ] Test coverage >90%

## Testing Strategy

### Unit Tests (30 tests)

```python
# tests/test_cli/test_prune.py

# prune --all
def test_prune_all_removes_all_venvs(tmp_path):
def test_prune_all_clears_cache(tmp_path):
def test_prune_all_requires_confirmation(tmp_path):
def test_prune_all_with_yes_flag(tmp_path):
def test_prune_all_dry_run(tmp_path):
def test_prune_all_empty_cache():

# prune --orphan
def test_prune_orphan_finds_orphans(tmp_path):
def test_prune_orphan_removes_only_orphans(tmp_path):
def test_prune_orphan_preserves_valid(tmp_path):
def test_prune_orphan_updates_cache(tmp_path):
def test_prune_orphan_no_orphans():
def test_prune_orphan_dry_run(tmp_path):
def test_prune_orphan_with_yes_flag(tmp_path):

# prune --current
def test_prune_current_removes_venv(tmp_path):
def test_prune_current_removes_cache_entry(tmp_path):
def test_prune_current_clears_env_file(tmp_path):
def test_prune_current_not_tracked_error():
def test_prune_current_not_in_project_error():
def test_prune_current_dry_run(tmp_path):

# prune <path>
def test_prune_path_removes_venv(tmp_path):
def test_prune_path_updates_cache_if_tracked(tmp_path):
def test_prune_path_untracked_venv(tmp_path):
def test_prune_path_rejects_dangerous_paths(tmp_path):
def test_prune_path_nonexistent_path():
def test_prune_path_dry_run(tmp_path):

# Safety and edge cases
def test_prune_mutual_exclusivity():
def test_prune_no_mode_error():
def test_prune_keyboard_interrupt(tmp_path):
def test_prune_partial_failure(tmp_path, mocker):
def test_prune_statistics_accuracy(tmp_path):
def test_prune_json_output(tmp_path):
```

### Integration Tests (4 tests)

```python
def test_prune_all_then_list(tmp_path):
    """Test that prune --all results in empty list"""

def test_init_then_prune_orphan(tmp_path):
    """Test orphan detection after project deletion"""

def test_prune_current_then_reinit(tmp_path):
    """Test that project can be reinitialized after prune"""

def test_multiple_orphan_types(tmp_path):
    """Test prune --orphan with various orphan reasons"""
```

### Manual Testing Checklist

- [ ] Run `prime-uve prune --all` and confirm deletion
- [ ] Test cancellation at confirmation prompt
- [ ] Initialize projects, delete one, run `prune --orphan`
- [ ] Run `prune --current` in initialized project
- [ ] Test `prune <path>` with specific venv path
- [ ] Try `prune /` and verify rejection
- [ ] Test `--dry-run` mode for all modes
- [ ] Test `--yes` flag skips confirmation
- [ ] Test `--json` output
- [ ] Verify statistics accuracy

## Design Decisions

### 1. Always Require Confirmation (Unless --yes)

**Decision:** All prune operations require explicit confirmation by default.

**Rationale:**
- Deletion is irreversible
- Prevents accidents
- Shows user exactly what will happen
- Industry standard (git, docker, etc.)

### 2. Show Detailed Preview Before Deletion

**Decision:** Display all venvs to be deleted with sizes before confirmation.

**Rationale:**
- User makes informed decision
- Transparency builds trust
- Helps identify mistakes before they happen

### 3. Validate Paths Strictly

**Decision:** Reject any path outside `~/prime-uve/venvs/`.

**Rationale:**
- Prevent accidental system damage
- Prime-uve only manages venvs in its directory
- Explicit is safer than flexible

### 4. Update Cache Atomically

**Decision:** Update cache only after successful deletion.

**Rationale:**
- Cache accurately reflects filesystem state
- Partial failures don't leave cache inconsistent
- Can retry deletions if needed

### 5. Clear .env.uve When Pruning Current

**Decision:** When using `--current`, clear .env.uve content but don't delete file.

**Rationale:**
- File may be tracked in git (should not disappear)
- Clearing content indicates "not configured"
- User can reinitialize easily

## Risk Assessment

### High Risk
- **Accidental deletion** - User runs wrong command
  - Mitigation: Always require confirmation, show preview

- **Partial deletion failures** - Some venvs fail to delete
  - Mitigation: Continue with others, report failures, don't corrupt cache

### Medium Risk
- **Large venvs** - Deletion could be slow
  - Mitigation: Show progress indicator for large operations

- **Permission errors** - Cannot delete some files
  - Mitigation: Clear error message with suggested fixes (chmod, sudo)

### Low Risk
- **Cache corruption** - Error during cache update
  - Mitigation: Cache uses file locking, atomic writes

## Documentation Requirements

### CLI Help Text

```
prime-uve prune [OPTIONS] [PATH]

  Clean up venv directories.

  Modes (choose one):
    --all              Remove ALL managed venvs and clear cache
    --orphan           Remove only orphaned venvs (project deleted/moved)
    --current          Remove current project's venv
    PATH               Remove venv at specific path

  Safety:
    • Always shows preview before deletion
    • Requires confirmation (use --yes to skip)
    • Use --dry-run to preview without deleting

Options:
  --all                      Remove all venvs
  --orphan                   Remove orphaned venvs only
  --current                  Remove current project venv
  -v, --verbose              Show detailed output
  -y, --yes                  Skip confirmation prompts
  --dry-run                  Show what would be deleted
  --json                     Output as JSON
  -h, --help                 Show this message and exit

Examples:
  prime-uve prune --orphan         # Clean up after deleted projects
  prime-uve prune --current        # Fresh start for current project
  prime-uve prune --all --dry-run  # Preview full cleanup
  prime-uve prune ~/prime-uve/venvs/myproject_a1b2  # Remove specific venv
```

### README.md Section

```markdown
## Clean Up Venvs

Remove orphaned venvs (from deleted projects):
```bash
prime-uve prune --orphan
```

Remove current project's venv:
```bash
prime-uve prune --current
```

Remove all venvs:
```bash
prime-uve prune --all
```

Preview without deleting:
```bash
prime-uve prune --orphan --dry-run
```

Skip confirmation (for scripts):
```bash
prime-uve prune --orphan --yes
```
```

## Success Metrics

- [ ] All 4 modes work correctly
- [ ] Confirmation prevents accidental deletions
- [ ] Dry run accurately predicts behavior
- [ ] Statistics are accurate
- [ ] Partial failures handled gracefully
- [ ] Cache stays consistent
- [ ] Clear error messages guide users
- [ ] Test coverage >90%
- [ ] No data loss in normal operation

## Next Task Dependencies

This task completes the core venv lifecycle:
- init → create venv
- list → inspect venvs
- prune → clean up venvs

Remaining Phase 3 tasks are independent:
- Task 3.5: `prime-uve activate` (shell integration)
- Task 3.6: `prime-uve configure vscode` (editor integration)

## Estimated Complexity

**High** - This is the most safety-critical command, requiring:
- Multiple complex modes
- Careful filesystem operations
- Robust error handling
- Extensive validation

Estimated effort: 5-7 hours including tests and documentation.
