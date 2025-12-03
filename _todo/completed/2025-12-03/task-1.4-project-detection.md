# Task 1.4: Implement Project Detection

**Parent Task**: Architecture Design for prime-uve CLI Tool
**Phase**: 1 - Core Infrastructure (Foundation)
**Status**: Proposal
**Dependencies**: Task 1.1 (Path Hashing System) ✅

## Objective

Implement project root detection and metadata extraction. This module provides utilities to locate Python project roots (by finding `pyproject.toml`) and extract project metadata needed for venv path generation and display.

## Context

Project detection is needed to:
- Find the correct location to create `.env.uve` files
- Extract project name for venv path generation (fallback if not in pyproject.toml)
- Validate that a directory is actually a Python project
- Provide context for error messages and CLI output

This is simpler than Tasks 1.2 and 1.3 but still important infrastructure that other components depend on.

## Deliverables

### 1. Core Module: `src/prime_uve/core/project.py`

#### Functions to Implement

##### `find_project_root(start_path: Path | None = None) -> Path | None`

```python
def find_project_root(start_path: Path | None = None) -> Path | None:
    """Find project root by locating pyproject.toml.

    Walks up directory tree from start_path until it finds a directory
    containing pyproject.toml. This is considered the project root.

    Args:
        start_path: Starting directory. Defaults to Path.cwd()

    Returns:
        Path to project root (directory containing pyproject.toml),
        or None if no pyproject.toml found

    Example:
        >>> root = find_project_root()
        >>> print(root)
        Path('/home/user/projects/myproject')
        >>> (root / "pyproject.toml").exists()
        True
    """
```

**Behavior**:
- Start at `start_path` (or cwd)
- Check for `pyproject.toml` in current directory
- If found, return current directory
- If not found, move up one level and repeat
- Stop at filesystem root
- Return `None` if no `pyproject.toml` found

##### `get_project_metadata(project_path: Path) -> ProjectMetadata`

```python
def get_project_metadata(project_path: Path) -> ProjectMetadata:
    """Extract project metadata from project directory.

    Reads pyproject.toml if present and extracts relevant information.
    Falls back to directory name for missing fields.

    Args:
        project_path: Path to project root directory

    Returns:
        ProjectMetadata with name, description, Python version, etc.

    Raises:
        ProjectError: If project_path is not a valid project

    Example:
        >>> metadata = get_project_metadata(Path("/home/user/myproject"))
        >>> metadata.name
        'myproject'
        >>> metadata.python_version
        '>=3.13'
    """
```

#### `ProjectMetadata` Dataclass

```python
from dataclasses import dataclass

@dataclass
class ProjectMetadata:
    """Project metadata extracted from pyproject.toml and filesystem."""

    name: str                          # Project name (from pyproject or dirname)
    path: Path                         # Absolute path to project root
    has_pyproject: bool                # True if pyproject.toml exists
    python_version: str | None         # requires-python field, if present
    description: str | None            # Project description, if present

    @property
    def display_name(self) -> str:
        """Human-readable project name for output."""
        return self.name

    @property
    def is_valid_python_project(self) -> bool:
        """True if this appears to be a valid Python project."""
        return self.has_pyproject
```

**Field Sources**:
- `name`: From `pyproject.toml` → `project.name`, fallback to directory name
- `path`: Resolved absolute path to project root
- `has_pyproject`: Whether `pyproject.toml` exists
- `python_version`: From `pyproject.toml` → `project.requires-python`
- `description`: From `pyproject.toml` → `project.description`

##### `is_python_project(path: Path) -> bool`

```python
def is_python_project(path: Path) -> bool:
    """Check if directory is a Python project.

    A directory is considered a Python project if it contains pyproject.toml.

    Args:
        path: Path to directory to check

    Returns:
        True if directory contains pyproject.toml, False otherwise

    Example:
        >>> is_python_project(Path("/home/user/myproject"))
        True
        >>> is_python_project(Path("/home/user/random-dir"))
        False
    """
```

#### `ProjectError` Exception

```python
class ProjectError(Exception):
    """Raised when project operations fail."""
    pass
```

### 2. Project Structure Updates

```
src/
  prime_uve/
    core/
      __init__.py          # Add exports
      cache.py             # Task 1.2
      env_file.py          # Task 1.3
      paths.py             # Task 1.1
      project.py           # New file
```

### 3. Dependencies

No new dependencies. Uses:
- `pathlib.Path` (stdlib)
- `tomllib` (stdlib, Python 3.11+)
- Task 1.1 for name sanitization (reuses `get_project_name()`)

**Note**: This task has some overlap with Task 1.1's `get_project_name()`. We should refactor to have a single source of truth:
- Move `get_project_name()` logic into this task
- Have Task 1.1 import from this module
- OR: Keep Task 1.1 separate and have this task call it

**Recommendation**: Keep Task 1.1 separate (lower-level utility). This task calls Task 1.1's `get_project_name()` for the name field.

### 4. Unit Tests: `tests/test_project.py`

#### Project Root Tests
```python
def test_find_project_root_in_root(tmp_path):
    """Finds project root when starting in root directory."""

def test_find_project_root_in_subdirectory(tmp_path):
    """Finds project root when starting in subdirectory."""

def test_find_project_root_nested_subdirectory(tmp_path):
    """Finds project root from deeply nested subdirectory."""

def test_find_project_root_not_found(tmp_path):
    """Returns None when no pyproject.toml found."""

def test_find_project_root_at_filesystem_root(tmp_path):
    """Stops at filesystem root without error."""

def test_find_project_root_custom_start_path(tmp_path):
    """Respects custom start_path parameter."""

def test_find_project_root_symlink(tmp_path):
    """Follows symlinks when searching."""
```

#### Metadata Tests
```python
def test_get_project_metadata_with_full_pyproject(tmp_path):
    """Extracts all metadata from complete pyproject.toml."""

def test_get_project_metadata_minimal_pyproject(tmp_path):
    """Handles minimal pyproject.toml (only [project] section)."""

def test_get_project_metadata_no_project_section(tmp_path):
    """Falls back to directory name if no [project] section."""

def test_get_project_metadata_no_pyproject(tmp_path):
    """Uses directory name when no pyproject.toml."""

def test_get_project_metadata_malformed_toml(tmp_path):
    """Handles malformed pyproject.toml gracefully."""

def test_get_project_metadata_empty_name(tmp_path):
    """Falls back to directory name if name field is empty."""

def test_get_project_metadata_missing_optional_fields(tmp_path):
    """Handles missing optional fields (description, etc.)."""

def test_get_project_metadata_invalid_path():
    """Raises ProjectError for non-existent path."""
```

#### Is Python Project Tests
```python
def test_is_python_project_with_pyproject(tmp_path):
    """Returns True for directory with pyproject.toml."""

def test_is_python_project_without_pyproject(tmp_path):
    """Returns False for directory without pyproject.toml."""

def test_is_python_project_empty_directory(tmp_path):
    """Returns False for empty directory."""

def test_is_python_project_file_not_directory(tmp_path):
    """Returns False for file path (not directory)."""
```

#### Integration Tests
```python
def test_full_workflow_find_and_get_metadata(tmp_path):
    """Find root then get metadata."""

def test_metadata_matches_paths_module(tmp_path):
    """Metadata.name matches get_project_name() from paths.py."""
```

#### Edge Cases
```python
def test_multiple_pyproject_in_hierarchy(tmp_path):
    """Finds nearest pyproject.toml when multiple exist."""

def test_special_chars_in_project_name(tmp_path):
    """Handles special characters in project name."""

def test_unicode_in_project_name(tmp_path):
    """Handles unicode in project name."""

def test_very_long_project_name(tmp_path):
    """Handles very long project names."""

def test_symlink_to_project(tmp_path):
    """Handles symlinked project directories."""

def test_network_path(tmp_path):
    """Handles UNC paths on Windows (if applicable)."""
```

## Implementation Plan

### Step 1: Implement Project Root Finding
1. Implement `find_project_root()` with directory walking
2. Test all scenarios (in root, in subdir, not found)
3. Handle filesystem root boundary
4. Test with symlinks

### Step 2: Implement Python Project Check
1. Implement `is_python_project()` (simple check)
2. Test positive and negative cases
3. Test edge cases (files, non-existent paths)

### Step 3: Implement Metadata Extraction
1. Define `ProjectMetadata` dataclass
2. Implement `get_project_metadata()` with TOML parsing
3. Use `get_project_name()` from Task 1.1 for name fallback
4. Extract optional fields (description, python_version)
5. Handle missing/malformed pyproject.toml

### Step 4: Error Handling
1. Define `ProjectError` exception
2. Add validation in `get_project_metadata()`
3. Test error scenarios

### Step 5: Integration Testing
1. Test find + metadata workflow
2. Test consistency with Task 1.1
3. Test with real project structures
4. Test cross-platform paths

## Acceptance Criteria

- ✅ `find_project_root()` correctly walks up directory tree
- ✅ Finds nearest `pyproject.toml` when multiple exist in hierarchy
- ✅ Returns `None` when no project root found (doesn't crash)
- ✅ Stops at filesystem root gracefully
- ✅ `is_python_project()` correctly identifies Python projects
- ✅ `get_project_metadata()` extracts all available metadata
- ✅ Falls back to directory name when `pyproject.toml` missing or incomplete
- ✅ Handles malformed `pyproject.toml` without crashing
- ✅ `ProjectMetadata.name` consistent with Task 1.1's `get_project_name()`
- ✅ All tests pass with >95% coverage
- ✅ Works on Windows, macOS, Linux
- ✅ Handles symlinks, special characters, unicode

## Example Usage

```python
from pathlib import Path
from prime_uve.core.project import (
    find_project_root,
    get_project_metadata,
    is_python_project,
)

# Find project root from anywhere in project tree
root = find_project_root()
if root is None:
    print("Not in a Python project")
else:
    print(f"Project root: {root}")

# Check if directory is a Python project
if is_python_project(Path("/some/path")):
    print("This is a Python project")

# Get detailed project metadata
root = find_project_root()
if root:
    metadata = get_project_metadata(root)
    print(f"Project: {metadata.name}")
    print(f"Python: {metadata.python_version or 'not specified'}")
    print(f"Description: {metadata.description or 'none'}")
    print(f"Valid project: {metadata.is_valid_python_project}")

# Usage in CLI commands
from prime_uve.core.project import find_project_root, ProjectError

root = find_project_root()
if root is None:
    print("Error: Not in a Python project. Run this command from a project directory.")
    sys.exit(1)

try:
    metadata = get_project_metadata(root)
    print(f"Initializing venv for {metadata.display_name}...")
except ProjectError as e:
    print(f"Error: {e}")
    sys.exit(1)
```

## Dependencies on Other Tasks

**This task depends on**:
- Task 1.1: Path Hashing System ✅ (uses `get_project_name()` for consistency)

**This task blocks**:
- Task 1.3: .env.uve Lookup (needs `find_project_root()`)
- Task 3.2: prime-uve init (needs project metadata)
- All CLI commands (need to validate user is in a project)

## Testing Strategy

### Unit Tests (with tmp_path)
- Create temporary project structures
- Create `pyproject.toml` files with various content
- Mock filesystem hierarchy

### Integration Tests
- Test with real project structures
- Test consistency with other modules (Task 1.1)
- Test error paths

### Cross-Platform Tests
- Test with Windows and Unix paths
- Test with UNC paths (Windows network shares)
- Test symlinks on Unix

## Edge Cases to Handle

1. **Multiple pyproject.toml files**: Find nearest one (closest to start_path)
2. **Symlinked projects**: Follow symlinks, resolve to real path
3. **Malformed TOML**: Catch parse errors, fall back to directory name
4. **Empty pyproject.toml**: Handle missing `[project]` section
5. **No name field**: Fall back to directory name
6. **Special characters**: Handle in project names and paths
7. **Unicode**: Support UTF-8 in all fields
8. **Very deep nesting**: No recursion limit issues
9. **Filesystem root**: Stop gracefully at `/` or drive root
10. **Permissions**: Handle unreadable `pyproject.toml` files

## Open Questions

1. **Should we support other project markers besides pyproject.toml?**
   - **Recommendation**: No. `pyproject.toml` is the standard for Python projects.

2. **Should we cache project root lookup results?**
   - **Recommendation**: No. Operations are fast enough, no caching needed.

3. **Should we validate pyproject.toml structure?**
   - **Recommendation**: No. Just extract what we need, ignore the rest.

4. **Should we expose more metadata fields (dependencies, scripts, etc.)?**
   - **Recommendation**: Not in v1. Keep it minimal (name, python version, description).

5. **Should find_project_root() return resolved path (symlinks followed)?**
   - **Recommendation**: Yes. Use `.resolve()` to get canonical path.

## Success Metrics

- All acceptance criteria met
- Test coverage ≥95%
- Consistent with Task 1.1 name extraction
- Ready for .env.uve lookup and CLI commands
- No crashes on malformed input
- Clear error messages

## Notes

- This is the simplest of the Phase 1 tasks (mostly straightforward filesystem operations)
- Key design choice: `find_project_root()` returns `None` if not found (doesn't raise)
- This allows calling code to decide how to handle "not in a project" scenario
- `get_project_metadata()` raises `ProjectError` if path invalid (requires valid input)
- Consistency with Task 1.1 is critical: same project → same name → same venv path
