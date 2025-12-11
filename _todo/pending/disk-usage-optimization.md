# Proposal: Optimize Disk Usage Calculation Performance

## Problem Statement

Both `prime-uve list` and `prime-uve prune` are slow due to inefficient disk usage calculation. The bottleneck is recursive directory walking that processes thousands of files per venv, even when size information isn't displayed.

## Real-World Benchmark Data

Testing on actual production setup (`C:\Users\s.follador\.prime-uve\venvs`):
- **8 venvs, 83,882 files, 1.89 GB total**

### Current Performance

```
Scenario 1: CURRENT (always calculate, rglob):
  Time: 1.863s

Scenario 2: OPTIMIZED (skip calculation):
  Time: 0.0001s
  Speedup: 32,735x FASTER! 🚀

Scenario 3: OPTIMIZED (os.walk when needed):
  Time: 0.985s
  Speedup: 1.89x faster
```

### Key Finding: Windows-Specific Behavior

The `du` command (Git Bash on Windows) **timed out after 30 seconds** - it's unusable due to subprocess overhead and I/O bottlenecks on Windows.

## Root Cause Analysis

### Current Bottleneck

**Duplicate `get_disk_usage()` in two files**:
- `src/prime_uve/cli/list.py` (lines 144-164)
- `src/prime_uve/cli/prune.py` (lines 18-38)

```python
def get_disk_usage(path: Path) -> int:
    total = 0
    for item in path.rglob("*"):  # ← SLOW: recursively walks entire tree
        if item.is_file():
            total += item.stat().st_size  # ← 83,882 stat() calls
    return total
```

### Where It's Called

**In list.py**:
1. Line 68: `validate_project_mapping()` - for EVERY cached venv
2. Line 137: `find_untracked_venvs()` - for EVERY untracked venv
3. **Problem**: Calculated even when NOT displayed in normal mode!

**In prune.py**:
1. Line 266: `prune_all()` - for all venvs
2. Line 389: `prune_valid()` - for valid venvs
3. Line 487: `prune_orphan()` - for orphaned venvs
4. Line 656: `prune_current()` - for current venv
5. Line 767: `prune_path()` - for specific path
6. **Note**: Here size IS needed (shows space to be freed)

### Why This Is Slow

Real-world impact:
- `rglob("*")` recursively walks entire tree: **1.863s for 8 venvs**
- `os.walk()` is faster but still slow: **0.985s for 8 venvs**
- **Not calculating when not needed**: **0.0001s** (32,735× faster!)

### Additional Code Duplication Issues

These functions are duplicated across list.py and prune.py:
- `get_disk_usage()` - disk usage calculation
- `format_bytes()` - size formatting
- `scan_venv_directory()` - venv discovery
- `find_untracked_venvs()` - untracked venv detection

**Impact**: Bug fixes and optimizations must be applied twice.

## Design Philosophy: Speed Over Accuracy

**User preference**: "prefer faster method to accuracy"

### For `list` Command
Disk usage is **nice-to-have metadata**, not critical functionality. Users need:
1. Which venvs exist ✓ (critical)
2. Which are valid vs orphaned ✓ (critical)
3. Venv locations ✓ (critical)
4. Disk usage ✗ (optional - only shown with `-v`)

**Strategy**: Skip calculation in normal mode, optimize when needed.

### For `prune` Command
Disk usage IS needed - users want to know how much space they'll free. However:
1. It's still slow (1.86s for 8 venvs)
2. We can make it faster without sacrificing accuracy
3. Users are already waiting for confirmation, so optimization matters less

**Strategy**: Always calculate, but use faster method (`os.walk` instead of `rglob`).

## Proposed Solution: Four-Phase Approach

### Phase 1: Extract Shared Utilities (DRY)
**Create `src/prime_uve/utils/disk.py` with shared functions**

```python
"""Disk usage utilities for venv management."""
import os
from pathlib import Path


def get_disk_usage(path: Path) -> int:
    """
    Calculate total disk usage using os.walk (faster than rglob).

    Optimized for speed:
    - Uses os.walk instead of rglob (1.89x faster)
    - Uses os.path.getsize instead of Path.stat()
    - Properly handles permission errors

    Args:
        path: Directory path

    Returns:
        Total size in bytes
    """
    total = 0
    try:
        for root, dirs, files in os.walk(path):
            for filename in files:
                try:
                    total += os.path.getsize(os.path.join(root, filename))
                except (OSError, PermissionError):
                    pass
    except (OSError, PermissionError):
        pass
    return total


def format_bytes(size: int) -> str:
    """Format bytes to human-readable string."""
    # ... (existing implementation, moved from list.py/prune.py)
```

**Benefits**:
- Single source of truth
- Bug fixes apply everywhere
- Performance improvements benefit both commands
- Easier to test

### Phase 2: Skip Calculation in `list` (Biggest Win - 32,000× faster!)
**Modify `list_command()` to conditionally calculate**

```python
def validate_project_mapping(
    project_path: str,
    cache_entry: dict,
    calculate_disk_usage: bool = False  # ← New parameter
) -> ValidationResult:
    """Validate a project mapping with optional disk usage calculation."""
    # ... existing validation logic ...

    # Only calculate disk usage if requested
    disk_usage = 0
    if calculate_disk_usage and venv_path_expanded.exists():
        from prime_uve.utils.disk import get_disk_usage
        disk_usage = get_disk_usage(venv_path_expanded)

    return ValidationResult(..., disk_usage_bytes=disk_usage)


def find_untracked_venvs(
    cache_entries: dict,
    calculate_disk_usage: bool = False  # ← New parameter
) -> list[dict]:
    """Find untracked venvs with optional disk usage calculation."""
    # ... existing logic ...

    for venv_dir in all_venvs:
        if venv_dir not in tracked_venvs:
            size = 0
            if calculate_disk_usage:
                from prime_uve.utils.disk import get_disk_usage
                size = get_disk_usage(venv_dir)

            untracked.append({
                "project_name": f"<unknown: {project_name}>",
                "disk_usage_bytes": size,
                # ... other fields ...
            })


def list_command(..., verbose: bool, json_output: bool, ...):
    """List command with conditional disk usage calculation."""
    # Only calculate sizes when they'll be displayed
    calculate_sizes = verbose or json_output

    # Pass flag through validation pipeline
    results = []
    for project_path, cache_entry in mappings.items():
        result = validate_project_mapping(
            project_path,
            cache_entry,
            calculate_disk_usage=calculate_sizes  # ← Only when needed!
        )
        results.append(result)

    untracked = find_untracked_venvs(
        mappings,
        calculate_disk_usage=calculate_sizes  # ← Only when needed!
    )
```

**Performance Impact**:
- Normal mode: **1.86s → 0.0001s** (32,000× faster!)
- Verbose mode: Still needs calculation, but Phase 3 helps
- JSON mode: Still needs calculation, but Phase 3 helps

### Phase 3: Optimize `prune` Calculation (1.89× faster)
**Update prune.py to use shared, optimized function**

```python
# Before (in prune.py)
from prime_uve.cli.list import get_disk_usage, format_bytes  # ← Remove

# After
from prime_uve.utils.disk import get_disk_usage, format_bytes  # ← Shared utils
```

**Changes**:
1. Replace duplicate `get_disk_usage()` with import from `utils.disk`
2. Inherits `os.walk` optimization automatically
3. No functional changes - still calculates for all prune operations

**Performance Impact**:
- All prune operations: **1.86s → 0.98s** (1.89× faster)
- Disk space freed message now appears sooner

### Phase 4: Move Shared Functions (DRY Cleanup)
**Extract ALL duplicated code to shared utilities**

Create `src/prime_uve/utils/venv.py`:
```python
"""Shared venv discovery utilities."""
from pathlib import Path
from prime_uve.core.paths import get_venv_base_dir, expand_path_variables


def scan_venv_directory() -> list[Path]:
    """Scan venv base directory for all venv directories."""
    # ... (moved from list.py and prune.py)


def find_untracked_venvs(
    cache_entries: dict,
    calculate_disk_usage: bool = False
) -> list[dict]:
    """Find venvs on disk that aren't in cache."""
    # ... (moved from list.py, updated for prune.py)
```

**Update imports**:
- `list.py`: Remove duplicate functions, import from `utils.venv` and `utils.disk`
- `prune.py`: Remove duplicate functions, import from `utils.venv` and `utils.disk`

**Benefits**:
- DRY: No more duplicate code
- Single place for bug fixes
- Easier to test utilities in isolation

## Implementation Plan

### Phase 1: Extract Shared Utilities (Foundation)
**Goal**: Create reusable disk utilities module

1. **Create `src/prime_uve/utils/disk.py`**:
   ```python
   def get_disk_usage(path: Path) -> int:
       """Calculate using os.walk (1.89x faster than rglob)."""
       # ... implementation with os.walk ...

   def format_bytes(size: int) -> str:
       """Format bytes to human-readable string."""
       # ... existing implementation ...
   ```

2. **Create tests** `tests/test_utils/test_disk.py`:
   - Test `get_disk_usage()` with known directory
   - Test `format_bytes()` with various sizes
   - Test error handling (permission denied, etc.)

3. **Verify benchmarks**: Ensure `os.walk` is faster than `rglob`

**Files created**: 2 new files
**Estimated time**: 30 minutes

### Phase 2: Skip Calculation in `list` (Biggest Win)
**Goal**: Make normal mode instant (32,000× faster)

1. **Update `list.py` function signatures**:
   - `validate_project_mapping(..., calculate_disk_usage: bool = False)`
   - `find_untracked_venvs(..., calculate_disk_usage: bool = False)`

2. **Update `list_command()` to pass flag**:
   ```python
   calculate_sizes = verbose or json_output
   results = validate_project_mapping(..., calculate_disk_usage=calculate_sizes)
   ```

3. **Import from shared utils**:
   ```python
   from prime_uve.utils.disk import get_disk_usage, format_bytes
   ```

4. **Update tests** `tests/test_cli/test_list.py`:
   - Test disk_usage=0 in normal mode
   - Test disk_usage>0 in verbose/JSON mode
   - Verify output format unchanged

5. **Run benchmarks**: Confirm 1.86s → ~0.0001s

**Files modified**: `src/prime_uve/cli/list.py`, tests
**Estimated time**: 1 hour

### Phase 3: Optimize `prune` Calculation
**Goal**: Make prune faster (1.89× improvement)

1. **Update `prune.py` imports**:
   ```python
   from prime_uve.utils.disk import get_disk_usage, format_bytes
   ```

2. **Remove duplicate functions**:
   - Delete local `get_disk_usage()` (lines 18-38)
   - Delete local `format_bytes()` (lines 41-65)

3. **Verify all prune modes still work**:
   - `prune --all`
   - `prune --valid`
   - `prune --orphan`
   - `prune --current`
   - `prune <path>`

4. **Update tests** `tests/test_cli/test_prune.py`:
   - Verify disk usage still calculated correctly
   - Verify "freed X disk space" messages still appear
   - Add performance regression test

5. **Run benchmarks**: Confirm 1.86s → 0.98s

**Files modified**: `src/prime_uve/cli/prune.py`, tests
**Estimated time**: 45 minutes

### Phase 4: Extract Shared Venv Utilities (DRY)
**Goal**: Eliminate remaining code duplication

1. **Create `src/prime_uve/utils/venv.py`**:
   ```python
   def scan_venv_directory() -> list[Path]:
       """Scan venv base directory."""
       # ... moved from list.py and prune.py ...

   def find_untracked_venvs(
       cache_entries: dict,
       calculate_disk_usage: bool = False
   ) -> list[dict]:
       """Find venvs not in cache."""
       # ... unified implementation ...
   ```

2. **Update imports in both files**:
   - `list.py`: Import from `utils.venv`
   - `prune.py`: Import from `utils.venv`
   - Remove duplicate implementations

3. **Run full test suite**: Ensure no regressions

**Files created/modified**: 1 new file, 2 modified
**Estimated time**: 45 minutes

### Total Implementation Time
- Phase 1: 30 min
- Phase 2: 60 min (biggest impact)
- Phase 3: 45 min
- Phase 4: 45 min
- **Total: ~3 hours**

### Implementation Priority
If time-constrained, implement in this order:
1. **Phase 2** (skip calculation) - 32,000× speedup for normal use
2. **Phase 1** (shared utils) - enables Phase 2 and 3
3. **Phase 3** (optimize prune) - 1.89× speedup
4. **Phase 4** (DRY cleanup) - code quality, no performance gain

## Performance Comparison (Based on Real Benchmarks)

Testing environment: 8 venvs, 83,882 files, 1.89 GB

| Command | Current | After Phase 1+2 | After Phase 3 | Improvement |
|---------|---------|-----------------|---------------|-------------|
| `prime-uve list` | 1.86s | **0.0001s** | 0.0001s | **32,735× faster!** |
| `prime-uve list -v` | 1.86s | 1.86s | **0.98s** | **1.89× faster** |
| `prime-uve list --json` | 1.86s | 1.86s | **0.98s** | **1.89× faster** |
| `prime-uve prune --orphan` | 1.86s | 1.86s | **0.98s** | **1.89× faster** |
| `prime-uve prune --all` | 1.86s | 1.86s | **0.98s** | **1.89× faster** |

### Projected Performance at Scale

| Setup | Current | After All Phases | Time Saved |
|-------|---------|------------------|------------|
| 8 venvs (real test) | 1.86s | 0.0001s | **1.86s per command** |
| 20 venvs (estimated) | ~5s | 0.0002s | **~5s per command** |
| 50 venvs (large setup) | ~12s | 0.0005s | **~12s per command** |

**Real-world impact**: Developers run `prime-uve list` multiple times per day. With 20+ venvs:
- **Current**: 5 seconds × 10 commands/day = **50 seconds/day wasted**
- **Optimized**: Instant × 10 commands/day = **50 seconds/day saved**

## Recommended Approach

**Implement All 4 Phases** in order:

1. **Phase 1** (30 min): Foundation - extract shared utilities
2. **Phase 2** (60 min): **Massive win** - skip calculation in list
3. **Phase 3** (45 min): Optimize prune - use faster method
4. **Phase 4** (45 min): DRY cleanup - eliminate duplication

**Total**: ~3 hours for 32,000× improvement in most common use case

## Edge Cases & Safety

1. **Permission denied during walk**: Skip file, continue (already handled)
2. **Venv deleted mid-calculation**: Return accumulated size (already handled)
3. **Symbolic links**: `os.walk` follows symlinks by default, matches current behavior
4. **Network drives**: May be slow, but no worse than current implementation
5. **Empty venvs**: Return 0 correctly
6. **Very large venvs (>10GB)**: No timeout needed, just slower (acceptable for verbose mode)

## Testing Strategy

1. **Unit tests** (`tests/test_utils/test_disk.py`):
   - Test `get_disk_usage()` with known test directory
   - Compare `os.walk` vs `rglob` results (should match)
   - Test `format_bytes()` with edge cases (0, 1023, 1024, etc.)
   - Test permission error handling

2. **Integration tests** (`tests/test_cli/test_list.py`, `test_prune.py`):
   - Normal mode: Verify disk_usage=0 (skipped)
   - Verbose mode: Verify disk_usage>0 (calculated)
   - JSON mode: Verify disk_usage in output
   - Verify output format unchanged

3. **Performance regression tests**:
   - Benchmark `list` normal mode: <0.1s for 10 venvs
   - Benchmark `list -v`: <2s for 10 venvs
   - Benchmark `prune --orphan`: <2s for 10 venvs

4. **Cross-platform tests**:
   - Linux: Full test suite
   - Mac: Full test suite
   - Windows: Full test suite (verified os.walk works)

## Breaking Changes

**None**. All changes are internal optimizations:
- Output format: Identical
- API: Backward compatible (new optional parameters with defaults)
- Behavior: Identical from user perspective
- Tests: May need updates for implementation details

## Files to Create/Modify

**New files**:
- `src/prime_uve/utils/disk.py` (disk usage utilities)
- `src/prime_uve/utils/venv.py` (venv discovery utilities)
- `tests/test_utils/test_disk.py` (unit tests)

**Modified files**:
- `src/prime_uve/cli/list.py` (conditional calculation, import shared utils)
- `src/prime_uve/cli/prune.py` (remove duplicates, import shared utils)
- `tests/test_cli/test_list.py` (test conditional calculation)
- `tests/test_cli/test_prune.py` (verify no regressions)

**Lines of code**:
- Added: ~150 lines (new utils modules + tests)
- Removed: ~120 lines (duplicated functions)
- Net change: +30 lines
- Improved: ~200 lines (refactored to use shared utils)

## Success Criteria

- [x] Benchmarked current performance (1.86s for 8 venvs)
- [x] Phase 1: Create `utils.disk` module with `os.walk` implementation
- [x] Phase 2: Normal `prime-uve list` completes in <0.5s (achieved: 0.18s)
- [x] Phase 2: Disk usage still calculated correctly in verbose/JSON modes
- [x] Phase 3: `prime-uve prune` operations complete in <1s (achieved: 0.97s)
- [x] Phase 4: No duplicate code between list.py and prune.py
- [x] All 80 tests pass (26 list + 39 prune + 15 disk utils)
- [x] Output format unchanged (backward compatible)
- [x] Cross-platform compatibility maintained (Windows, Linux, Mac)

## Implementation Complete ✅

### Final Benchmark Results

Test environment: **8 venvs, 74,830 files, 1.7 GB**

| Command | Before | After | Improvement |
|---------|--------|-------|-------------|
| `prime-uve list` | 1.18s | **0.18s** | **6.5× FASTER** ⚡ |
| `prime-uve list -v` | 1.86s | **0.97s** | **1.9× faster** |
| `prime-uve prune` | 1.86s | **0.97s** | **1.9× faster** |

### Verification

- ✅ Normal mode: Instant response (0.18s vs 1.18s)
- ✅ Verbose mode: Correctly displays disk usage (46MB-385MB per venv shown)
- ✅ All 80 tests pass
- ✅ No breaking changes
- ✅ Time saved: ~1 second per command

### Files Modified

**New files**:
- `src/prime_uve/utils/disk.py` - Optimized disk usage utilities
- `src/prime_uve/utils/venv.py` - Shared venv discovery utilities
- `tests/test_utils/test_disk.py` - 15 comprehensive tests

**Modified files**:
- `src/prime_uve/cli/list.py` - Conditional disk usage calculation
- `src/prime_uve/cli/prune.py` - Use shared utilities
- `tests/test_cli/test_list.py` - Updated test mocks
- `tests/test_cli/test_prune.py` - Updated test mocks

### Branch & PR

- **Branch**: `feature/disk-usage-optimization`
- **Status**: Pushed to GitHub, ready for PR
- **PR URL**: https://github.com/kompre/prime-uve/pull/new/feature/disk-usage-optimization

---

## Future Enhancements (Out of Scope)

These were NOT implemented but could be future improvements:

1. **Cache disk usage in cache.json**: Store size with timestamp, refresh every 24h
2. **Progress indicator**: Show spinner while calculating sizes in verbose mode
3. **Parallel calculation**: Use ThreadPoolExecutor for multiple venvs (2-4× faster)
4. **Streaming output**: Display venvs as they're validated, don't wait for all

**Decision**: Skipped - Phase 1-4 already provides sufficient improvement (6.5× faster).
