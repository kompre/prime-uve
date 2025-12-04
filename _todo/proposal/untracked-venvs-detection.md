# Task Proposal: Detect and Report Untracked Venvs

## Problem Statement

Currently, `prime-uve list` only shows venvs that are tracked in the cache (`~/.prime-uve/cache.json`). However, there may be venv directories in the storage location (`~/prime-uve/venvs/`) that are not tracked in the cache. These untracked venvs are invisible to the system and cannot be cleaned up with `prime-uve prune --orphan`.

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

Enhance `prime-uve list` and `prime-uve prune` to detect and report untracked venvs.

### Option A: Enhanced List Command (Recommended)

Add a new validation category to `prime-uve list`:
- **Valid**: Cache matches .env.uve (current)
- **Orphan**: Cache doesn't match .env.uve (current)
- **Untracked**: Venv exists on disk but not in cache (NEW)

**Implementation**:
1. Scan `~/prime-uve/venvs/` directory
2. Compare against cache entries
3. Report venvs that exist on disk but not in cache

**Output Example**:
```bash
$ prime-uve list

Managed Virtual Environments

PROJECT              STATUS          VENV PATH
--------------------------------------------------------------------------------
prime-uve            [!] Orphan      ~/prime-uve/venvs/prime-uve_043331fa
<unknown>            [?] Untracked   ~/prime-uve/venvs/test-project_0e688aca
<unknown>            [?] Untracked   ~/prime-uve/venvs/test-project_15fb9ebc
...

Summary: 1 tracked (0 valid, 1 orphaned), 57 untracked
Total disk usage: 2.5 GB

Note: Untracked venvs are not managed by prime-uve.
Run 'prime-uve prune --untracked' to clean them up.
```

### Option B: Separate Command

Create a new command `prime-uve scan` to detect untracked venvs:
```bash
$ prime-uve scan
Found 57 untracked venv(s) in ~/prime-uve/venvs/
Total disk usage: 2.4 GB

Run 'prime-uve prune --untracked' to clean them up.
```

**Pros**:
- Doesn't clutter `list` output
- Focused tool for maintenance

**Cons**:
- Extra command to learn
- User needs to know to run it

## Recommended Approach: Option A (Enhanced List)

Enhance existing commands rather than adding new ones.

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
    """Find venvs on disk that aren't in cache."""
    all_venvs = scan_venv_directory()
    tracked_venvs = set()

    for cache_entry in cache_entries.values():
        venv_path_expanded = expand_path_variables(cache_entry["venv_path"])
        tracked_venvs.add(venv_path_expanded)

    untracked = []
    for venv_dir in all_venvs:
        if venv_dir not in tracked_venvs:
            untracked.append({
                "venv_path_expanded": venv_dir,
                "disk_usage_bytes": get_disk_usage(venv_dir),
            })

    return untracked
```

**Output Changes**:
- Add new status symbol: `[?] Untracked`
- Show untracked venvs after tracked ones
- Update summary to include untracked count
- Add helpful message about `prune --untracked`

**Options**:
- `--untracked-only`: Show only untracked venvs
- Existing `--orphan-only` still works (shows only cached orphans)

#### 2. Update `prime-uve prune`

Add new mode: `prime-uve prune --untracked`

**Changes to `prune.py`**:
```python
def prune_untracked(ctx, verbose, yes, dry_run, json_output):
    """Remove untracked venv directories."""
    # 1. Load cache to know what's tracked
    cache = Cache()
    tracked_venvs = get_tracked_venv_paths(cache)

    # 2. Scan disk for all venvs
    all_venvs = scan_venv_directory()

    # 3. Find untracked ones
    untracked = [v for v in all_venvs if v not in tracked_venvs]

    # 4. Show and confirm
    # 5. Delete (with --dry-run support)
    # 6. Do NOT update cache (they're not in it)
```

**Command Usage**:
```bash
# Remove all untracked venvs
prime-uve prune --untracked --yes

# Preview what would be removed
prime-uve prune --untracked --dry-run

# Remove ALL venvs (tracked + untracked)
prime-uve prune --all  # Already removes everything in the directory
```

**Note**: `prune --all` already removes everything in `~/prime-uve/venvs/`, so it handles untracked venvs. But `--untracked` is more surgical.

#### 3. Update Validation Logic

Current validation only checks cached entries. We need to also check disk:

```python
class VenvStatus:
    """Status of a venv."""
    VALID = "valid"           # In cache, matches .env.uve
    ORPHAN = "orphan"         # In cache, doesn't match .env.uve
    UNTRACKED = "untracked"   # On disk, not in cache
```

## Acceptance Criteria

- [ ] `prime-uve list` shows untracked venvs with `[?] Untracked` status
- [ ] `prime-uve list --untracked-only` filters to show only untracked venvs
- [ ] Summary includes untracked count: "1 tracked (0 valid, 1 orphaned), 57 untracked"
- [ ] `prime-uve prune --untracked` removes only untracked venvs
- [ ] `prime-uve prune --all` still removes everything (tracked + untracked)
- [ ] Dry-run works for `--untracked` mode
- [ ] JSON output includes untracked venvs with proper status
- [ ] Verbose mode shows which venvs are untracked
- [ ] Disk usage is calculated and displayed for untracked venvs
- [ ] No false positives (venvs correctly identified as tracked vs untracked)
- [ ] Performance is acceptable with 100+ venvs on disk
- [ ] Comprehensive test coverage for new functionality

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

def test_prune_untracked():
    """Test prune --untracked mode."""
    # Create untracked venvs, prune them

def test_list_untracked_only_filter():
    """Test --untracked-only filter."""
    # Mix of statuses, filter shows only untracked
```

### Integration Tests
```python
def test_untracked_workflow():
    """Test full workflow: create untracked, list, prune."""
    # 1. Create venv manually in storage dir
    # 2. Verify list shows it as untracked
    # 3. Prune it
    # 4. Verify it's gone
```

## Files to Modify

- `src/prime_uve/cli/list.py` - Add untracked detection and display
- `src/prime_uve/cli/prune.py` - Add `--untracked` mode
- `tests/test_cli/test_list.py` - Add untracked tests
- `tests/test_cli/test_prune.py` - Add untracked prune tests
- `_todo/pending/architecture-design.md` - Document this enhancement

## Alternative: Import Untracked Venvs

Instead of just deleting untracked venvs, could we try to "import" them back into the cache?

**Challenges**:
1. Can't determine original project path from venv directory alone
2. Hash in directory name doesn't reverse to project path
3. Would need to scan entire filesystem to find matching projects
4. May match wrong project if multiple projects have same name

**Verdict**: Too complex and unreliable. Better to just clean them up.

## Migration Path

For users with existing untracked venvs:

1. **Awareness**: First time running `list` after upgrade, show message:
   ```
   [i] Found 57 untracked venvs (2.4 GB) not managed by prime-uve.
   [i] Run 'prime-uve list --untracked-only' to see them.
   [i] Run 'prime-uve prune --untracked' to clean them up.
   ```

2. **Gradual cleanup**: Users can review with `--untracked-only` before pruning

3. **Safe default**: `prune --orphan` still only touches cached orphans (safer)

## Questions for User

1. **Should `list` always show untracked venvs, or hide them by default?**
   - Option A: Always show (more visibility, but noisier)
   - Option B: Hide by default, show with `--show-untracked` flag
   - **Recommendation**: Always show, with helpful message

2. **Should `prune --all` behavior change?**
   - Current: Removes everything in `~/prime-uve/venvs/` directory
   - Proposed: No change (still removes everything)
   - **Recommendation**: Keep current behavior

3. **Should we try to prevent untracked venvs from being created?**
   - Could add validation in init to check if venv dir already exists
   - **Recommendation**: Not needed, prune handles cleanup

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

1. **Visibility**: Users can see all venvs consuming space
2. **Cleanup**: Can remove untracked venvs safely
3. **Debugging**: Helps diagnose cache sync issues
4. **Disk management**: Better control over disk usage
5. **Trust**: System shows everything, not just cached items
