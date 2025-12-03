# Task 1.2: Implement Cache System

**Parent Task**: Architecture Design for prime-uve CLI Tool
**Phase**: 1 - Core Infrastructure (Foundation)
**Status**: Proposal
**Dependencies**: Task 1.1 (Path Hashing System) ✅

## Objective

Implement a persistent, thread-safe caching system to track project → venv mappings. This enables validation of venv status (exists, orphaned, path mismatches) and supports the `list` and `prune` commands.

## Context

The cache system is the "source of truth" for all managed venvs. It needs to:
- Persist across program invocations
- Support concurrent access (multiple terminals, background processes)
- Validate mappings against filesystem reality
- Support migration for future schema changes
- Be resilient to corruption

Cache location: `$HOME/.prime-uve/cache.json`

## Deliverables

### 1. Core Module: `src/prime_uve/core/cache.py`

#### Cache Schema (JSON)

```json
{
  "version": "1.0",
  "venvs": {
    "/absolute/path/to/project": {
      "venv_path": "${HOME}/prime-uve/venvs/myproject_a1b2c3d4",
      "venv_path_expanded": "/home/user/prime-uve/venvs/myproject_a1b2c3d4",
      "project_name": "myproject",
      "path_hash": "a1b2c3d4",
      "created_at": "2025-12-03T12:00:00Z",
      "last_validated": "2025-12-03T12:00:00Z"
    }
  }
}
```

**Field Descriptions**:
- `version`: Cache schema version for future migrations
- `venv_path`: Path with `${HOME}` variable (cross-platform)
- `venv_path_expanded`: Platform-specific expanded path (for validation only)
- `project_name`: Sanitized project name
- `path_hash`: 8-char hash from project path
- `created_at`: ISO 8601 timestamp when venv was created
- `last_validated`: ISO 8601 timestamp of last validation check

#### `Cache` Class

```python
class Cache:
    """Thread-safe cache for project → venv mappings."""

    def __init__(self, cache_path: Path | None = None):
        """Initialize cache.

        Args:
            cache_path: Path to cache file. Defaults to ~/.prime-uve/cache.json
        """

    def add_mapping(
        self,
        project_path: Path,
        venv_path: str,
        project_name: str,
        path_hash: str
    ) -> None:
        """Add or update a project → venv mapping.

        Args:
            project_path: Absolute path to project directory
            venv_path: Venv path with ${HOME} variable (not expanded)
            project_name: Sanitized project name
            path_hash: 8-character hash

        Raises:
            CacheError: If cache cannot be written
        """

    def get_mapping(self, project_path: Path) -> dict | None:
        """Get mapping for a project.

        Args:
            project_path: Absolute path to project directory

        Returns:
            Mapping dict or None if not found
        """

    def remove_mapping(self, project_path: Path) -> bool:
        """Remove a project → venv mapping.

        Args:
            project_path: Absolute path to project directory

        Returns:
            True if removed, False if not found
        """

    def list_all(self) -> dict[str, dict]:
        """Get all cached mappings.

        Returns:
            Dict of project_path → mapping
        """

    def validate_mapping(self, project_path: Path) -> ValidationResult:
        """Validate a mapping against filesystem reality.

        Checks:
        - Project directory exists
        - Venv directory exists (using expanded path)
        - .env.uve exists and contains matching venv path

        Args:
            project_path: Absolute path to project directory

        Returns:
            ValidationResult with status and issues
        """

    def validate_all(self) -> dict[str, ValidationResult]:
        """Validate all cached mappings.

        Returns:
            Dict of project_path → ValidationResult
        """

    def clear(self) -> None:
        """Remove all mappings from cache."""

    def migrate_if_needed(self) -> None:
        """Migrate cache to current version if needed.

        Called automatically on load. Future-proofing for schema changes.
        """
```

#### `ValidationResult` Dataclass

```python
@dataclass
class ValidationResult:
    """Result of validating a cached mapping."""

    status: Literal["valid", "orphaned", "mismatch", "error"]
    issues: list[str]  # Human-readable issue descriptions

    @property
    def is_valid(self) -> bool:
        """True if status is 'valid'."""
        return self.status == "valid"

    @property
    def is_orphaned(self) -> bool:
        """True if project or venv is missing."""
        return self.status == "orphaned"

    @property
    def has_mismatch(self) -> bool:
        """True if .env.uve path doesn't match cache."""
        return self.status == "mismatch"
```

**Validation Logic**:
- `valid`: All checks pass
- `orphaned`: Project dir missing OR venv dir missing OR .env.uve missing
- `mismatch`: .env.uve exists but path doesn't match cache
- `error`: Unexpected error during validation (permissions, etc.)

#### `CacheError` Exception

```python
class CacheError(Exception):
    """Raised when cache operations fail."""
    pass
```

### 2. File Locking Strategy

Use `filelock` library for cross-platform file locking:

```python
from filelock import FileLock

class Cache:
    def __init__(self, cache_path: Path | None = None):
        self._cache_path = cache_path or self._default_cache_path()
        self._lock_path = self._cache_path.with_suffix(".lock")
        self._lock = FileLock(self._lock_path, timeout=10)

    def _load(self) -> dict:
        """Load cache with lock held."""
        with self._lock:
            if not self._cache_path.exists():
                return {"version": "1.0", "venvs": {}}
            with open(self._cache_path) as f:
                return json.load(f)

    def _save(self, data: dict) -> None:
        """Save cache with lock held."""
        with self._lock:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._cache_path, "w") as f:
                json.dump(data, f, indent=2)
```

**Timeout Handling**: 10-second timeout for lock acquisition. If exceeded, raise `CacheError` with actionable message.

### 3. Project Structure Updates

```
src/
  prime_uve/
    core/
      __init__.py          # Add Cache export
      cache.py             # New file
      paths.py             # Existing (Task 1.1)
```

### 4. Dependencies

Add to `pyproject.toml`:
```toml
dependencies = [
    "filelock>=3.0.0",
]
```

### 5. Unit Tests: `tests/test_cache.py`

#### Basic Operations Tests
```python
def test_add_mapping():
    """Adding a mapping persists it."""

def test_get_mapping():
    """Getting a mapping returns correct data."""

def test_get_mapping_not_found():
    """Getting non-existent mapping returns None."""

def test_remove_mapping():
    """Removing a mapping deletes it."""

def test_remove_mapping_not_found():
    """Removing non-existent mapping returns False."""

def test_list_all_empty():
    """Empty cache returns empty dict."""

def test_list_all_multiple():
    """List all returns all mappings."""

def test_clear():
    """Clear removes all mappings."""
```

#### Persistence Tests
```python
def test_persistence_across_instances():
    """Mappings persist when cache is reloaded."""

def test_cache_created_if_missing():
    """Cache file is created on first write."""

def test_cache_directory_created():
    """Parent directory is created if missing."""
```

#### Validation Tests
```python
def test_validate_mapping_valid():
    """Validation passes when everything exists and matches."""

def test_validate_mapping_project_missing():
    """Validation detects missing project directory."""

def test_validate_mapping_venv_missing():
    """Validation detects missing venv directory."""

def test_validate_mapping_env_file_missing():
    """Validation detects missing .env.uve file."""

def test_validate_mapping_path_mismatch():
    """Validation detects when .env.uve path differs from cache."""

def test_validate_all():
    """Validate all returns results for all mappings."""

def test_validation_updates_last_validated():
    """Validation updates last_validated timestamp."""
```

#### Concurrency Tests
```python
def test_concurrent_writes(tmp_path):
    """Multiple processes can write without corruption."""
    # Use multiprocessing to simulate concurrent access

def test_lock_timeout():
    """Lock timeout raises CacheError with clear message."""
```

#### Edge Cases
```python
def test_corrupted_cache_file():
    """Invalid JSON is handled gracefully."""

def test_missing_fields_in_mapping():
    """Missing fields in mappings don't crash."""

def test_update_existing_mapping():
    """Updating existing mapping preserves created_at."""

def test_long_project_paths():
    """Very long project paths work correctly."""

def test_special_chars_in_paths():
    """Paths with spaces, unicode work correctly."""
```

#### Migration Tests
```python
def test_migrate_if_needed_no_op():
    """Migration is no-op for current version."""

def test_migrate_if_needed_adds_version():
    """Missing version field is added during migration."""

# Future: Add tests for actual migrations when schema changes
```

## Implementation Plan

### Step 1: Set Up Dependencies
1. Add `filelock` to `pyproject.toml`
2. Run `uv sync` to install
3. Update `src/prime_uve/core/__init__.py` to export `Cache`

### Step 2: Implement Core Cache Class
1. Implement `__init__` with cache path defaults
2. Implement `_load()` and `_save()` with file locking
3. Implement basic CRUD: `add_mapping()`, `get_mapping()`, `remove_mapping()`
4. Implement `list_all()` and `clear()`
5. Write tests for basic operations

### Step 3: Implement Validation
1. Define `ValidationResult` dataclass
2. Implement `validate_mapping()` with all checks
3. Implement `validate_all()`
4. Write validation tests with mock filesystem

### Step 4: Add Migration Support
1. Implement `migrate_if_needed()`
2. Call migration in `_load()`
3. Write migration tests

### Step 5: Error Handling
1. Define `CacheError` exception
2. Add error handling for file operations
3. Add timeout handling for locks
4. Write error scenario tests

### Step 6: Integration Testing
1. Test with real filesystem operations
2. Test concurrent access with multiprocessing
3. Test validation with actual .env.uve files
4. Performance test with 100+ mappings

## Acceptance Criteria

- ✅ Cache persists across program invocations
- ✅ Concurrent access doesn't corrupt cache (file locking)
- ✅ Validation correctly identifies:
  - Valid mappings (all files exist, paths match)
  - Orphaned mappings (project or venv missing)
  - Mismatched mappings (.env.uve path differs)
- ✅ Invalid/corrupted cache files handled gracefully
- ✅ Missing cache directory created automatically
- ✅ Lock timeout raises clear error message
- ✅ All tests pass with >95% coverage
- ✅ Works on Windows, macOS, Linux
- ✅ Performance acceptable with 100+ cached venvs
- ✅ `venv_path` always stored with `${HOME}` variable
- ✅ `venv_path_expanded` uses platform-specific home directory

## Example Usage

```python
from pathlib import Path
from prime_uve.core.cache import Cache
from prime_uve.core.paths import generate_venv_path, generate_hash, get_project_name

# Initialize cache (defaults to ~/.prime-uve/cache.json)
cache = Cache()

# Add a mapping
project_path = Path("/mnt/share/my-project").resolve()
venv_path = generate_venv_path(project_path)
project_name = get_project_name(project_path)
path_hash = generate_hash(project_path)

cache.add_mapping(
    project_path=project_path,
    venv_path=venv_path,
    project_name=project_name,
    path_hash=path_hash
)

# Get mapping
mapping = cache.get_mapping(project_path)
print(mapping["venv_path"])  # ${HOME}/prime-uve/venvs/my-project_a1b2c3d4

# Validate mapping
result = cache.validate_mapping(project_path)
if result.is_valid:
    print("✓ Valid")
elif result.is_orphaned:
    print(f"✗ Orphaned: {', '.join(result.issues)}")
elif result.has_mismatch:
    print(f"⚠ Mismatch: {', '.join(result.issues)}")

# List all
for project_path, mapping in cache.list_all().items():
    result = cache.validate_mapping(Path(project_path))
    print(f"{project_path}: {result.status}")

# Remove mapping
cache.remove_mapping(project_path)
```

## Dependencies on Other Tasks

**This task depends on**:
- Task 1.1: Path Hashing System ✅ (uses `generate_venv_path`, `expand_path_variables`)

**This task blocks**:
- Task 3.2: prime-uve init (needs cache to store mappings)
- Task 3.3: prime-uve list (needs cache to list all venvs)
- Task 3.4: prime-uve prune (needs validation to identify orphans)

## Testing Strategy

### Unit Tests (with tmp_path fixtures)
- Create temporary cache files for each test
- Mock filesystem for validation tests
- Use pytest fixtures for common setup

### Concurrency Tests
- Use `multiprocessing` to simulate concurrent access
- Verify no corruption with parallel writes
- Test lock acquisition and timeout

### Integration Tests
- Create real project directories with .env.uve files
- Create real venv directories
- Test validation against real filesystem

### Performance Tests
- Create cache with 100+ mappings
- Measure load/save/validate_all performance
- Ensure acceptable performance (<1s for operations)

## Edge Cases to Handle

1. **Corrupted JSON**: Invalid JSON in cache.json → rebuild cache or return empty
2. **Missing fields**: Old cache format missing fields → migrate or use defaults
3. **Symlinks**: Project path is symlink → resolve before storing
4. **Network drives**: Cache on network drive → may have slower I/O, handle timeouts
5. **Permissions**: No write permission to cache dir → clear error message
6. **Race conditions**: Two processes adding same mapping → last write wins (acceptable)
7. **Lock stale**: Process crashed while holding lock → filelock handles cleanup
8. **Long paths**: Windows MAX_PATH issues → use \\\\?\\ prefix if needed

## Open Questions

1. **Cache location override**: Should we support `PRIME_UVE_CACHE` env var?
   - **Recommendation**: Yes, for testing and advanced users

2. **Validation frequency**: Should we cache validation results to avoid repeated filesystem checks?
   - **Recommendation**: Not in v1. Validation is fast enough. Can optimize later if needed.

3. **Automatic cleanup**: Should we auto-prune orphaned venvs after N days?
   - **Recommendation**: No, explicit only. User should decide when to prune.

4. **Multiple caches**: Support per-project caches in addition to global?
   - **Recommendation**: No, keep simple. Global cache only.

## Success Metrics

- All acceptance criteria met
- Test coverage ≥95%
- No data loss during concurrent access
- Clear error messages for all failure modes
- Performance acceptable with 100+ venvs
- Ready for CLI commands (init, list, prune) to be implemented

## Notes

- File locking is critical: multiple terminals, background processes may access cache
- Validation is "lazy": only runs when explicitly called (by `list`, `prune`, etc.)
- Cache corruption recovery: if JSON invalid, log warning and start with empty cache
- `venv_path_expanded` stored in cache to avoid re-expanding on every validation (performance)
- Timestamps use ISO 8601 format for human readability and parseability
