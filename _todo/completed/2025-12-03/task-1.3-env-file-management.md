# Task 1.3: Implement .env.uve File Management

**Parent Task**: Architecture Design for prime-uve CLI Tool
**Phase**: 1 - Core Infrastructure (Foundation)
**Status**: Proposal
**Dependencies**: Task 1.1 (Path Hashing System) ✅

## Objective

Implement the .env.uve file lookup, read, and write operations with variable-aware parsing. This module handles finding .env.uve files in the directory tree, parsing them without expanding variables, and writing them with proper cross-platform variable syntax.

## Context

The `.env.uve` file is critical to the entire system:
- Must use expandable variables (`${HOME}`) for cross-platform compatibility
- Same file must work on Windows, macOS, Linux
- Supports network share scenario (multiple users, same file)
- Must never expand variables when reading/writing (expansion happens at runtime by `uv`)
- Needs smart lookup logic: current dir → walk up to project root → create if missing

## Deliverables

### 1. Core Module: `src/prime_uve/core/env_file.py`

#### File Format

```bash
# .env.uve - SAME on all platforms
UV_PROJECT_ENVIRONMENT=${HOME}/prime-uve/venvs/myproject_a1b2c3d4

# Can contain other environment variables
# PYTHONPATH=/some/path
# CUSTOM_VAR=value
```

**Critical Constraints**:
- Must use `${HOME}` (never `${USERPROFILE}`, `%USERPROFILE%`, or absolute paths)
- Variables must NOT be expanded when reading/writing
- Expansion happens at runtime by `uv` (and by our code only for local validation)

#### Functions to Implement

##### `find_env_file(start_path: Path | None = None) -> Path`

```python
def find_env_file(start_path: Path | None = None) -> Path:
    """Find or create .env.uve file using smart lookup logic.

    Search algorithm:
    1. Check current directory for .env.uve
    2. If not found, walk up directory tree to project root (pyproject.toml)
    3. If found project root without .env.uve, create empty one there
    4. If no project root found, create .env.uve in start_path

    Args:
        start_path: Starting directory. Defaults to Path.cwd()

    Returns:
        Path to .env.uve file (always returns a path, creates if needed)

    Example:
        >>> env_file = find_env_file()
        >>> print(env_file)
        /home/user/projects/myproject/.env.uve
    """
```

**Lookup Logic Details**:
```
Scenario 1: .env.uve in current directory
  /project/
    pyproject.toml
    .env.uve          ← Found immediately
    subdir/
      [cwd]

Scenario 2: .env.uve at project root
  /project/
    pyproject.toml
    .env.uve          ← Walk up and find
    subdir/
      [cwd]

Scenario 3: No .env.uve, has project root
  /project/
    pyproject.toml
    [.env.uve]        ← Create here
    subdir/
      [cwd]

Scenario 4: No project root (no pyproject.toml)
  /some/dir/
    [cwd]
    [.env.uve]        ← Create in cwd
```

##### `read_env_file(path: Path) -> dict[str, str]`

```python
def read_env_file(path: Path) -> dict[str, str]:
    """Read .env.uve file and parse variables WITHOUT expanding them.

    Parsing rules:
    - Lines with '=' are key-value pairs
    - Leading/trailing whitespace stripped from keys and values
    - Comments (lines starting with #) ignored
    - Empty lines ignored
    - Variables (${...}) are NOT expanded, kept as-is

    Args:
        path: Path to .env.uve file

    Returns:
        Dict of variable name → value (with variables unexpanded)

    Raises:
        EnvFileError: If file cannot be read or parsed

    Example:
        >>> env = read_env_file(Path(".env.uve"))
        >>> env["UV_PROJECT_ENVIRONMENT"]
        '${HOME}/prime-uve/venvs/myproject_a1b2c3d4'  # NOT expanded
    """
```

**Parsing Rules**:
- Simple line-by-line parsing (no shell interpolation)
- Format: `KEY=value` (no spaces around `=`)
- Comments start with `#` (ignore entire line)
- Empty lines ignored
- No quote handling needed (values are literal)
- Variables preserved as-is (`${HOME}` stays `${HOME}`)

##### `write_env_file(path: Path, env_vars: dict[str, str]) -> None`

```python
def write_env_file(path: Path, env_vars: dict[str, str]) -> None:
    """Write environment variables to .env.uve file.

    Variables are written as-is (not expanded). If variables contain
    expandable syntax like ${HOME}, they are preserved.

    Args:
        path: Path to .env.uve file
        env_vars: Dict of variable name → value

    Raises:
        EnvFileError: If file cannot be written

    Example:
        >>> write_env_file(
        ...     Path(".env.uve"),
        ...     {"UV_PROJECT_ENVIRONMENT": "${HOME}/prime-uve/venvs/proj_abc123"}
        ... )
    """
```

**Format**:
```bash
KEY1=value1
KEY2=value2
```

**Notes**:
- No comments (clean output)
- Alphabetical order for consistency
- One variable per line
- No quotes around values
- Unix line endings (`\n`) even on Windows (git handles this)

##### `update_env_file(path: Path, updates: dict[str, str]) -> None`

```python
def update_env_file(path: Path, updates: dict[str, str]) -> None:
    """Update specific variables in .env.uve file, preserving others.

    Args:
        path: Path to .env.uve file
        updates: Dict of variables to add/update

    Raises:
        EnvFileError: If file cannot be read or written

    Example:
        >>> update_env_file(
        ...     Path(".env.uve"),
        ...     {"UV_PROJECT_ENVIRONMENT": "${HOME}/prime-uve/venvs/proj_new"}
        ... )
    """
```

##### `get_venv_path(env_vars: dict[str, str], expand: bool = False) -> str | Path`

```python
def get_venv_path(env_vars: dict[str, str], expand: bool = False) -> str | Path:
    """Extract venv path from parsed environment variables.

    Args:
        env_vars: Parsed environment variables from read_env_file()
        expand: If True, expand ${HOME} to actual path. If False, return as-is.

    Returns:
        If expand=False: str with variables (e.g., "${HOME}/...")
        If expand=True: Path with variables expanded (e.g., Path("/home/user/..."))

    Raises:
        EnvFileError: If UV_PROJECT_ENVIRONMENT not found

    Example:
        >>> env = read_env_file(Path(".env.uve"))
        >>> get_venv_path(env, expand=False)
        '${HOME}/prime-uve/venvs/myproject_a1b2c3d4'
        >>> get_venv_path(env, expand=True)
        Path('/home/user/prime-uve/venvs/myproject_a1b2c3d4')
    """
```

**Uses `expand_path_variables()` from Task 1.1** when `expand=True`.

#### `EnvFileError` Exception

```python
class EnvFileError(Exception):
    """Raised when .env.uve operations fail."""
    pass
```

### 2. Project Structure Updates

```
src/
  prime_uve/
    core/
      __init__.py          # Add exports
      cache.py             # Task 1.2
      env_file.py          # New file
      paths.py             # Task 1.1
```

### 3. Dependencies

No new dependencies (uses only stdlib + pathlib + Task 1.1).

### 4. Unit Tests: `tests/test_env_file.py`

#### Lookup Tests
```python
def test_find_env_file_in_current_dir(tmp_path):
    """Finds .env.uve in current directory."""

def test_find_env_file_walk_up_to_root(tmp_path):
    """Walks up directory tree to project root."""

def test_find_env_file_create_at_project_root(tmp_path):
    """Creates .env.uve at project root if missing."""

def test_find_env_file_create_in_cwd_no_project(tmp_path):
    """Creates .env.uve in cwd if no project root found."""

def test_find_env_file_stops_at_filesystem_root(tmp_path):
    """Stops walking up at filesystem root."""

def test_find_env_file_custom_start_path(tmp_path):
    """Respects custom start_path parameter."""
```

#### Read Tests
```python
def test_read_env_file_basic(tmp_path):
    """Reads basic key=value pairs."""

def test_read_env_file_preserves_variables(tmp_path):
    """Variables like ${HOME} are NOT expanded."""

def test_read_env_file_ignores_comments(tmp_path):
    """Lines starting with # are ignored."""

def test_read_env_file_ignores_empty_lines(tmp_path):
    """Empty lines are ignored."""

def test_read_env_file_strips_whitespace(tmp_path):
    """Leading/trailing whitespace is stripped."""

def test_read_env_file_empty_file(tmp_path):
    """Empty file returns empty dict."""

def test_read_env_file_missing_file(tmp_path):
    """Missing file raises EnvFileError."""

def test_read_env_file_permission_denied(tmp_path):
    """Permission denied raises EnvFileError."""
```

#### Write Tests
```python
def test_write_env_file_basic(tmp_path):
    """Writes basic key=value pairs."""

def test_write_env_file_preserves_variables(tmp_path):
    """Variables like ${HOME} are written as-is."""

def test_write_env_file_sorted_keys(tmp_path):
    """Keys are written in sorted order."""

def test_write_env_file_overwrites_existing(tmp_path):
    """Overwrites existing file."""

def test_write_env_file_creates_parent_dirs(tmp_path):
    """Creates parent directories if missing."""

def test_write_env_file_empty_dict(tmp_path):
    """Empty dict creates empty file."""

def test_write_env_file_permission_denied(tmp_path):
    """Permission denied raises EnvFileError."""
```

#### Update Tests
```python
def test_update_env_file_adds_new_var(tmp_path):
    """Adding new variable preserves existing ones."""

def test_update_env_file_updates_existing_var(tmp_path):
    """Updating existing variable changes only that one."""

def test_update_env_file_creates_file_if_missing(tmp_path):
    """Creates file if it doesn't exist."""

def test_update_env_file_preserves_order(tmp_path):
    """Variables are sorted alphabetically."""
```

#### Get Venv Path Tests
```python
def test_get_venv_path_no_expand(tmp_path):
    """Returns path with variables unexpanded."""

def test_get_venv_path_expand(tmp_path):
    """Expands ${HOME} when expand=True."""

def test_get_venv_path_missing_var():
    """Raises EnvFileError if UV_PROJECT_ENVIRONMENT not found."""

def test_get_venv_path_empty_value():
    """Raises EnvFileError if UV_PROJECT_ENVIRONMENT is empty."""
```

#### Integration Tests
```python
def test_full_workflow_find_read_write(tmp_path):
    """Full workflow: find → read → update → read again."""

def test_cross_platform_path_preserved(tmp_path):
    """${HOME} syntax preserved through read/write cycle."""

def test_multiple_variables(tmp_path):
    """Multiple environment variables handled correctly."""
```

#### Edge Cases
```python
def test_malformed_lines_ignored(tmp_path):
    """Lines without '=' are ignored gracefully."""

def test_equals_in_value(tmp_path):
    """Values containing '=' are handled correctly."""

def test_unicode_in_values(tmp_path):
    """Unicode characters in values work correctly."""

def test_very_long_values(tmp_path):
    """Very long values work correctly."""

def test_symlink_env_file(tmp_path):
    """Symlinked .env.uve files work correctly."""
```

## Implementation Plan

### Step 1: Implement File Lookup
1. Implement `find_env_file()` with directory walking logic
2. Test all lookup scenarios (4 scenarios from spec)
3. Handle edge cases (filesystem root, permissions)

### Step 2: Implement File Reading
1. Implement `read_env_file()` with line-by-line parsing
2. Ensure variables are NOT expanded
3. Test comment handling, empty lines, whitespace
4. Add error handling for missing/unreadable files

### Step 3: Implement File Writing
1. Implement `write_env_file()` with sorted output
2. Ensure variables are preserved as-is
3. Test file creation, overwriting
4. Add error handling for write failures

### Step 4: Implement Update Logic
1. Implement `update_env_file()` using read + write
2. Test partial updates preserve other variables
3. Test file creation if missing

### Step 5: Implement Venv Path Extraction
1. Implement `get_venv_path()` with optional expansion
2. Use `expand_path_variables()` from Task 1.1 when expanding
3. Test both modes (expanded and unexpanded)
4. Add error handling for missing variable

### Step 6: Integration Testing
1. Test full workflow: find → read → write → read
2. Test with real project structures
3. Test variable preservation through multiple read/write cycles
4. Test cross-platform scenarios (mock different platforms)

## Acceptance Criteria

- ✅ `find_env_file()` correctly walks up directory tree to project root
- ✅ Creates `.env.uve` at project root if missing
- ✅ Falls back to cwd if no project root found
- ✅ Stops at filesystem root (doesn't infinite loop)
- ✅ `read_env_file()` parses .env format correctly
- ✅ Variables (${HOME}) are NOT expanded during reading
- ✅ Comments and empty lines ignored
- ✅ `write_env_file()` writes sorted, clean output
- ✅ Variables preserved as-is (not expanded)
- ✅ `update_env_file()` preserves existing variables
- ✅ `get_venv_path()` extracts UV_PROJECT_ENVIRONMENT correctly
- ✅ Expansion mode works correctly using Task 1.1 function
- ✅ Error handling for missing/unreadable files
- ✅ All tests pass with >95% coverage
- ✅ Works on Windows, macOS, Linux

## Example Usage

```python
from pathlib import Path
from prime_uve.core.env_file import (
    find_env_file,
    read_env_file,
    write_env_file,
    update_env_file,
    get_venv_path,
)

# Find or create .env.uve
env_file = find_env_file()
print(f"Found: {env_file}")

# Read without expanding variables
env_vars = read_env_file(env_file)
print(env_vars)
# {'UV_PROJECT_ENVIRONMENT': '${HOME}/prime-uve/venvs/myproject_a1b2c3d4'}

# Get venv path (unexpanded)
venv_path_var = get_venv_path(env_vars, expand=False)
print(venv_path_var)
# '${HOME}/prime-uve/venvs/myproject_a1b2c3d4'

# Get venv path (expanded for local operations)
venv_path_expanded = get_venv_path(env_vars, expand=True)
print(venv_path_expanded)
# Path('/home/user/prime-uve/venvs/myproject_a1b2c3d4')

# Write new .env.uve (variables preserved)
write_env_file(
    env_file,
    {
        "UV_PROJECT_ENVIRONMENT": "${HOME}/prime-uve/venvs/myproject_a1b2c3d4",
        "PYTHONPATH": "/some/path",
    }
)

# Update specific variable
update_env_file(
    env_file,
    {"UV_PROJECT_ENVIRONMENT": "${HOME}/prime-uve/venvs/myproject_new"}
)
```

## Dependencies on Other Tasks

**This task depends on**:
- Task 1.1: Path Hashing System ✅ (uses `expand_path_variables()`)

**This task blocks**:
- Task 2.1: uve Wrapper (needs `find_env_file()`, `read_env_file()`)
- Task 3.2: prime-uve init (needs `write_env_file()`)
- Task 3.3: prime-uve list (needs validation with .env.uve)
- Task 3.5: prime-uve activate (needs to read all env vars)

## Testing Strategy

### Unit Tests (with tmp_path)
- Create temporary .env.uve files for each test
- Mock filesystem structure (projects with/without pyproject.toml)
- Test all parsing edge cases

### Integration Tests
- Create real project structures
- Test lookup in complex directory hierarchies
- Test read/write cycles preserve data

### Cross-Platform Tests
- Mock `Path.home()` to test different platforms
- Verify `${HOME}` works consistently
- Test on Windows and Unix paths

## Edge Cases to Handle

1. **No pyproject.toml**: Create .env.uve in cwd
2. **Filesystem root**: Stop walking up at `/` or drive root
3. **Symlinks**: Follow symlinks during directory walk
4. **Malformed lines**: Ignore lines without `=`
5. **Empty values**: Allow empty values (`KEY=`)
6. **Equals in value**: Handle `KEY=value=with=equals`
7. **Long lines**: No artificial line length limits
8. **Unicode**: Support UTF-8 in keys and values
9. **Permissions**: Clear error if cannot read/write
10. **Concurrent access**: Last write wins (no locking needed, file is small)

## Open Questions

1. **Should we validate that venv paths use ${HOME}?**
   - **Recommendation**: No, be permissive. Users may have custom setups.

2. **Should we support .env (without .uve extension)?**
   - **Recommendation**: No, keep it separate. `.env` often has secrets.

3. **Should we preserve comments when updating?**
   - **Recommendation**: No, too complex. Keep writes simple (no comments).

4. **Should we support quotes around values?**
   - **Recommendation**: No, literal values only. Simplifies parsing.

5. **Should read_env_file() expand any variables?**
   - **Recommendation**: NO. Expansion only happens via `expand=True` in `get_venv_path()` or explicitly by caller.

## Success Metrics

- All acceptance criteria met
- Test coverage ≥95%
- No variable expansion during read/write (critical!)
- Works seamlessly with Task 1.1 expansion function
- Ready for uve wrapper and CLI commands
- Variable preservation verified through multiple read/write cycles

## Notes

- **Critical**: Never expand variables during read/write. This breaks cross-platform compatibility.
- Parsing is intentionally simple (no shell interpolation, no quotes, no escaping)
- Git will handle line endings (`.gitattributes` can enforce LF)
- No file locking needed: .env.uve is small, writes are atomic, last write wins is acceptable
- `find_env_file()` always returns a path (creates file if needed) - never returns None
