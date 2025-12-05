# Task Proposal: Include Untracked Venvs as Orphans

## Problem Statement

Currently, `prime-uve list` only shows venvs that are tracked in the cache (`~/.prime-uve/cache.json`). However, there may be venv directories in the storage location (`~/prime-uve/venvs/`) that are not tracked in the cache. These venvs are invisible to the system and cannot be cleaned up with `prime-uve prune --orphan`.

**Current Behavior**:
```bash
$ ls ~/prime-uve/venvs/ | wc -l
58  # 58 venvs on disk

$ prime-uve list
Summary: 1 total, 0 valid, 1 orphaned  # Only 1 tracked in cache
```

The other 57 venvs are "invisible" - they consume disk space but aren't managed by prime-uve.

## Root Cause

This situation can occur when:
1. The cache file (`~/.prime-uve/cache.json`) is deleted or corrupted
2. Venvs are created manually in the storage directory
3. Cache entries are removed but venv directories remain
4. Tests create venvs that aren't properly cleaned up
5. Cache gets out of sync with filesystem

## Proposed Solution

**Treat untracked venvs as orphans** - they're not linked to any project we know about, so they're orphaned by definition.

Enhance `prime-uve list` and `prime-uve prune --orphan` to:
1. Scan the filesystem for all venvs
2. Include venvs not in cache as orphans
3. Clean them up with existing `prune --orphan` command

### Simplified Categories

- **Valid**: Cache matches .env.uve
- **Orphan**: Cache doesn't match .env.uve OR not in cache at all

No new status needed - untracked venvs are just another type of orphan.

**Output Example**:
```bash
$ prime-uve list

Managed Virtual Environments

PROJECT              STATUS          VENV PATH
--------------------------------------------------------------------------------
prime-uve            [!] Orphan      ~/prime-uve/venvs/prime-uve_043331fa
<unknown>            [!] Orphan      ~/prime-uve/venvs/test-project_0e688aca
<unknown>            [!] Orphan      ~/prime-uve/venvs/test-project_15fb9ebc
...

Summary: 58 total, 0 valid, 58 orphaned
Total disk usage: 2.5 GB

Found 58 orphaned venv(s). Run 'prime-uve prune --orphan' to clean up.
```

### Rationale

A venv that's not tracked in the cache is orphaned because:
- We don't know which project it belongs to
- We can't validate it against any .env.uve
- It's taking up disk space with no way to manage it
- It should be cleaned up

This is simpler than creating a new "untracked" category.

### Implementation Plan

#### 1. Update `prime-uve list`

**Changes to `list.py`**:
```python
def scan_venv_directory() -> list[Path]:
    """Scan venv base directory for all venv directories."""
    venv_base = get_venv_base_dir()
    if not venv_base.exists():
        return []
    return [d for d in venv_base.iterdir() if d.is_dir()]

def find_untracked_venvs(cache_entries: dict) -> list[dict]:
    """Find venvs on disk that aren't in cache (treat as orphans)."""
    all_venvs = scan_venv_directory()
    tracked_venvs = set()

    for cache_entry in cache_entries.values():
        venv_path_expanded = expand_path_variables(cache_entry["venv_path"])
        tracked_venvs.add(venv_path_expanded)

    untracked = []
    for venv_dir in all_venvs:
        if venv_dir not in tracked_venvs:
            # Extract project name from directory name (e.g., "test-project_abc123" -> "test-project")
            dir_name = venv_dir.name
            project_name = dir_name.rsplit('_', 1)[0] if '_' in dir_name else dir_name

            untracked.append({
                "project_name": f"<unknown: {project_name}>",
                "venv_path_expanded": venv_dir,
                "disk_usage_bytes": get_disk_usage(venv_dir),
                "is_valid": False,  # Treat as orphan
            })

    return untracked
```

**Output Changes**:
- Include untracked venvs in results with `[!] Orphan` status
- Show project name as `<unknown: project-name>` for untracked venvs
- Count them in orphan total
- `--orphan-only` now includes untracked venvs (they're orphans)

#### 2. Update `prime-uve prune --orphan`

**Changes to `prune.py`**:

No new mode needed! Just enhance `prune_orphan()` to include untracked venvs:

```python
def prune_orphan(ctx, verbose, yes, dry_run, json_output):
    """Remove orphaned venv directories (including untracked)."""
    # 1. Load cache
    cache = Cache()
    mappings = cache.list_all()

    # 2. Find cached orphans (current logic)
    orphaned_venvs = []
    for project_path, cache_entry in mappings.items():
        if is_orphaned(project_path, cache_entry):
            orphaned_venvs.append(...)

    # 3. Find untracked venvs (NEW)
    tracked_venvs = {expand_path_variables(e["venv_path"])
                     for e in mappings.values()}
    all_venvs = scan_venv_directory()

    for venv_dir in all_venvs:
        if venv_dir not in tracked_venvs:
            # This is an untracked venv - treat as orphan
            orphaned_venvs.append({
                "project_name": f"<unknown: {venv_dir.name}>",
                "venv_path": str(venv_dir),  # No variable form
                "venv_path_expanded": str(venv_dir),
                "size": get_disk_usage(venv_dir),
            })

    # 4. Remove all orphans (cached + untracked)
    # ... existing removal logic
```

**Benefits**:
- No new command to learn
- `prune --orphan` now cleans up everything that's orphaned
- Simpler mental model: orphan = not connected to a valid project

## Acceptance Criteria

- [ ] `prime-uve list` shows untracked venvs with `[!] Orphan` status
- [ ] Untracked venvs show project name as `<unknown: project-name>`
- [ ] Summary includes untracked venvs in orphan count
- [ ] `prime-uve prune --orphan` removes both cached orphans AND untracked venvs
- [ ] `prime-uve prune --all` still removes everything (no change)
- [ ] `--orphan-only` filter includes untracked venvs
- [ ] Dry-run works correctly with untracked venvs
- [ ] JSON output includes untracked venvs as orphans
- [ ] Verbose mode shows all venvs being removed
- [ ] Disk usage is calculated and displayed for untracked venvs
- [ ] No false positives (venvs correctly identified as tracked vs untracked)
- [ ] Performance is acceptable with 100+ venvs on disk
- [ ] Comprehensive test coverage for new functionality
- [ ] No cache corruption (untracked venvs don't get added to cache)

## Test Cases

### Unit Tests
```python
def test_scan_venv_directory():
    """Test scanning venv directory."""
    # Create venv dirs, verify scanning works

def test_find_untracked_venvs_none():
    """Test when all venvs are tracked."""
    # All venvs in cache, should return empty list

def test_find_untracked_venvs_some():
    """Test when some venvs are untracked."""
    # Mix of tracked and untracked

def test_find_untracked_venvs_all():
    """Test when all venvs are untracked."""
    # Empty cache, venvs on disk

def test_list_includes_untracked_as_orphans():
    """Test list shows untracked venvs as orphans."""
    # Create untracked venvs, verify they appear with orphan status

def test_prune_orphan_includes_untracked():
    """Test prune --orphan removes untracked venvs."""
    # Create untracked venvs, prune with --orphan, verify removed

def test_untracked_venv_project_name_extraction():
    """Test extracting project name from venv directory."""
    # "test-project_abc123" -> "<unknown: test-project>"
```

### Integration Tests
```python
def test_untracked_workflow():
    """Test full workflow: create untracked, list, prune."""
    # 1. Create venv manually in storage dir
    # 2. Verify list shows it as orphan
    # 3. Prune with --orphan
    # 4. Verify it's gone
```

## Files to Modify

- `src/prime_uve/cli/list.py` - Add filesystem scanning and include untracked as orphans
- `src/prime_uve/cli/prune.py` - Enhance `--orphan` mode to include untracked
- `tests/test_cli/test_list.py` - Add untracked tests
- `tests/test_cli/test_prune.py` - Add untracked prune tests
- `_todo/pending/architecture-design.md` - Document this enhancement

## Alternative: Import Untracked Venvs

Instead of just treating untracked venvs as orphans, could we try to "import" them back into the cache?

**Challenges**:
1. Can't determine original project path from venv directory alone
2. Hash in directory name doesn't reverse to project path
3. Would need to scan entire filesystem to find matching projects
4. May match wrong project if multiple projects have same name

**Verdict**: Too complex and unreliable. Better to treat them as orphans and let user clean them up.

## Migration Path

For users with existing untracked venvs:

1. **Automatic discovery**: After upgrade, `list` will automatically show them as orphans
   ```
   Summary: 58 total, 0 valid, 58 orphaned
   ```

2. **Gradual cleanup**: Users can review with `list` before pruning

3. **Behavior change**: `prune --orphan` now removes more (includes untracked)
   - This is the correct behavior - orphans should include untracked
   - Users who want to keep untracked venvs can skip using `--orphan`

## Priority

**High** - This is a usability issue affecting disk space management. Users may have gigabytes of "invisible" venvs consuming space without realizing it.

## Estimated Complexity

**Medium** - Not complex logic, but requires:
- Filesystem scanning
- Status comparison logic
- UI updates across two commands
- Comprehensive testing

Similar complexity to implementing a new prune mode (task 3.4 level).

## Related Issues

- Orphan detection only works for cached entries
- No way to discover venvs created outside prime-uve
- Cache corruption leads to "lost" venvs
- Test cleanup may leave untracked venvs

## Benefits

1. **Visibility**: Users can see all venvs consuming space, not just cached ones
2. **Cleanup**: `prune --orphan` now handles all orphaned venvs (cached + untracked)
3. **Debugging**: Helps diagnose cache sync issues
4. **Disk management**: Better control over disk usage
5. **Trust**: System shows everything, not just cached items
6. **Simplicity**: No new status category or command - just better orphan detection

---

## Completion Summary

**Completed**: 2025-12-05

### Implementation Status: ✅ COMPLETED

The untracked venvs feature has been successfully implemented. Based on git commits:
- d45b731: "list unknown venv as orphaned"
- cadaaf1: "Simplify untracked venvs proposal: treat as orphans"
- efb2a03: "Add task proposal: detect and clean untracked venvs"

### What Was Implemented

1. **Filesystem Scanning**: Added ability to scan venv directory for all venvs on disk
2. **Untracked Detection**: Identify venvs not present in cache
3. **Orphan Classification**: Treat untracked venvs as orphans (not as separate category)
4. **List Command**: Display untracked venvs with `[!] Orphan` status and `<unknown>` project name
5. **Prune Integration**: `prime-uve prune --orphan` now removes both cached orphans and untracked venvs

### Design Decision

Simplified approach: Treat untracked venvs as orphans rather than creating a new "untracked" status category. This keeps the mental model simple - if we don't know what project a venv belongs to (either because it's untracked or because the project is gone), it's orphaned.

### Files Modified

- `src/prime_uve/cli/list.py` - Added filesystem scanning and untracked detection
- `src/prime_uve/cli/prune.py` - Enhanced orphan pruning to include untracked venvs
- Test files updated accordingly

### Outcome

Users can now see all venvs consuming disk space (not just cached ones) and clean them up with the existing `prune --orphan` command. No new commands or status categories were added - just better orphan detection.
