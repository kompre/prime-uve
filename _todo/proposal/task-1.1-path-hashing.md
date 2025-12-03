# Task 1.1: Implement Path Hashing System

**Parent Task**: Architecture Design for prime-uve CLI Tool
**Phase**: 1 - Core Infrastructure (Foundation)
**Status**: Proposal

## Objective

Create deterministic, collision-resistant path hashing and cross-platform variable-based path generation system. This is the foundational module that generates unique venv paths using `${HOME}` for cross-platform compatibility.

## Context

From the architecture design, this module is critical because:
- All venv paths must use `${HOME}` variable (not platform-specific variables)
- Must work identically on Windows, macOS, Linux
- Supports network share scenario where same project accessed from multiple platforms
- Hash must be deterministic: same project path → same hash every time
- Hash must be collision-resistant: different paths → different hashes

## Deliverables

### 1. Core Module: `src/prime_uve/core/paths.py`

Functions to implement:

#### `generate_hash(project_path: Path) -> str`
- Input: Absolute path to project directory
- Output: 8-character hex hash
- Algorithm: First 8 chars of SHA256(normalized_absolute_path)
- Normalization: Use `.resolve().as_posix()` for cross-platform consistency

#### `generate_venv_path(project_path: Path) -> str`
- Input: Absolute path to project directory
- Output: Path string with `${HOME}` variable (NOT expanded)
- Format: `${HOME}/prime-uve/venvs/{project_name}_{hash}`
- **Critical**: Must return string with literal `${HOME}`, not expanded path

#### `expand_path_variables(path: str) -> Path`
- Input: Path string with variables (e.g., `${HOME}/...`)
- Output: Expanded pathlib.Path
- Logic:
  - Replace `${HOME}` with actual home directory
  - On Windows: Use `USERPROFILE` env var or `os.path.expanduser('~')`
  - On Unix/macOS: Use `HOME` env var or `os.path.expanduser('~')`
- Use for: Local validation only (checking if venv exists)

#### `get_project_name(project_path: Path) -> str`
- Input: Absolute path to project directory
- Output: Sanitized project name
- Logic:
  1. Try to read `pyproject.toml` and extract `project.name`
  2. If fails or not found, use parent directory name
  3. Sanitize: lowercase, replace non-alphanumeric with `-`
- Handle: Missing pyproject.toml, malformed TOML, missing name field

#### `ensure_home_set() -> None`
- Purpose: Ensure HOME environment variable is set (for Windows compatibility)
- Logic:
  - Check if `HOME` in `os.environ`
  - If not set and on Windows: Set `os.environ['HOME'] = os.environ['USERPROFILE']`
  - If USERPROFILE also missing: Set to `os.path.expanduser('~')`
- Use: Call before operations that need HOME variable

### 2. Project Structure

```
src/
  prime_uve/
    __init__.py              # Create package
    core/
      __init__.py            # Create subpackage
      paths.py               # Implementation
```

### 3. Unit Tests: `tests/test_paths.py`

Test cases to implement:

#### Hash Determinism Tests
```python
def test_generate_hash_deterministic():
    """Same path always generates same hash"""

def test_generate_hash_collision_resistance():
    """Different paths generate different hashes"""

def test_generate_hash_cross_platform():
    """Hash is same regardless of path separator style"""
```

#### Path Generation Tests
```python
def test_generate_venv_path_format():
    """Generated path uses ${HOME} variable"""

def test_generate_venv_path_includes_hash():
    """Generated path includes project name and hash"""

def test_generate_venv_path_not_expanded():
    """Generated path contains literal ${HOME}, not expanded"""
```

#### Variable Expansion Tests
```python
def test_expand_path_variables_home():
    """${HOME} expands to actual home directory"""

def test_expand_path_variables_windows(monkeypatch):
    """On Windows, uses USERPROFILE"""

def test_expand_path_variables_unix(monkeypatch):
    """On Unix, uses HOME env var"""
```

#### Project Name Tests
```python
def test_get_project_name_from_pyproject():
    """Extracts name from pyproject.toml"""

def test_get_project_name_fallback_to_dirname():
    """Uses directory name if no pyproject.toml"""

def test_get_project_name_sanitization():
    """Sanitizes special characters: 'My Project!' -> 'my-project'"""

def test_get_project_name_malformed_toml():
    """Handles malformed pyproject.toml gracefully"""
```

#### Edge Cases
```python
def test_generate_hash_long_path():
    """Handles very long paths"""

def test_generate_hash_special_chars():
    """Handles paths with spaces, unicode, etc."""

def test_generate_hash_symlinks():
    """Resolves symlinks before hashing"""
```

### 4. Dependencies

Update `pyproject.toml`:
```toml
[project]
name = "prime-uve"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "tomli>=2.0.0; python_version < '3.11'",  # For reading pyproject.toml
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
]
```

Note: Python 3.11+ has `tomllib` built-in, but we need `tomli` for 3.13 since we're using it.

Actually, wait - we're requiring Python 3.13, which has `tomllib` built-in. So no external dependency needed for TOML parsing.

```toml
[project]
name = "prime-uve"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
]
```

## Implementation Plan

### Step 1: Set Up Project Structure
1. Create directory structure: `src/prime_uve/core/`
2. Create `__init__.py` files
3. Update `pyproject.toml` with dev dependencies

### Step 2: Implement Hash Generation
1. Implement `generate_hash()` with SHA256
2. Write tests for determinism and collision resistance
3. Test cross-platform path normalization

### Step 3: Implement Path Generation
1. Implement `generate_venv_path()` using hash
2. Ensure it returns `${HOME}` literal (not expanded)
3. Write tests to verify format

### Step 4: Implement Variable Expansion
1. Implement `expand_path_variables()` for local validation
2. Handle Windows/Unix differences
3. Write tests with mocked environment variables

### Step 5: Implement Project Name Extraction
1. Implement `get_project_name()` with TOML parsing
2. Add fallback to directory name
3. Implement sanitization logic
4. Write tests with temp directories and pyproject.toml files

### Step 6: Implement HOME Ensure Logic
1. Implement `ensure_home_set()` for Windows compatibility
2. Test on Windows (or mock platform)

### Step 7: Integration Testing
1. Create integration test with real directory structure
2. Test full workflow: project path → hash → venv path → expansion
3. Verify cross-platform consistency

## Acceptance Criteria

- [ ] `generate_hash()` produces deterministic 8-char hashes
- [ ] Same project path always generates same hash
- [ ] Different paths generate different hashes (collision resistant)
- [ ] Hash is same regardless of platform (Windows paths vs Unix paths)
- [ ] `generate_venv_path()` returns string with `${HOME}` literal
- [ ] Generated path format: `${HOME}/prime-uve/venvs/{name}_{hash}`
- [ ] `expand_path_variables()` correctly expands `${HOME}` to actual directory
- [ ] Works on Windows (uses USERPROFILE), macOS, Linux (uses HOME)
- [ ] `get_project_name()` extracts name from pyproject.toml
- [ ] Falls back to directory name if no pyproject.toml
- [ ] Sanitizes names: spaces→hyphens, uppercase→lowercase, special chars removed
- [ ] Handles malformed pyproject.toml without crashing
- [ ] All tests pass (>95% coverage)
- [ ] Edge cases handled: long paths, special chars, symlinks, unicode

## Example Usage

```python
from pathlib import Path
from prime_uve.core.paths import (
    generate_hash,
    generate_venv_path,
    expand_path_variables,
    get_project_name,
)

# Generate venv path for a project
project_path = Path("/mnt/share/my-project")

# Get project name
name = get_project_name(project_path)  # "my-project"

# Generate hash
hash_val = generate_hash(project_path)  # "a1b2c3d4"

# Generate venv path (with variable)
venv_path = generate_venv_path(project_path)
# Result: "${HOME}/prime-uve/venvs/my-project_a1b2c3d4"

# For local operations, expand the variable
venv_path_expanded = expand_path_variables(venv_path)
# Result on Linux: Path("/home/user/prime-uve/venvs/my-project_a1b2c3d4")
# Result on Windows: Path("C:/Users/user/prime-uve/venvs/my-project_a1b2c3d4")

# Check if venv exists locally
if venv_path_expanded.exists():
    print("Venv already exists")
```

## Testing Strategy

### Unit Tests (Fast)
- Test each function in isolation
- Mock file system operations
- Mock environment variables
- Use pytest fixtures for temp directories

### Integration Tests (Slower)
- Create real temp directories
- Create real pyproject.toml files
- Test full workflow end-to-end

### Cross-Platform Tests
- Use `sys.platform` checks or mocking
- Test both Windows and Unix behaviors
- CI should test on multiple platforms

## Dependencies on Other Tasks

**This task blocks**:
- Task 1.2: Cache System (needs venv path generation)
- Task 1.3: .env.uve Lookup (needs path utilities)
- Task 3.2: prime-uve init (needs path generation)

**This task depends on**: None (it's the foundation)

## Estimated Complexity

**Low-Medium**: ~2-3 hours for experienced developer
- Core logic is straightforward (hashing, string manipulation)
- Main complexity is in cross-platform testing
- TOML parsing with error handling needs care

## Open Questions

1. **Hash collision handling**: What if two different projects generate same 8-char hash?
   - **Decision**: Acceptable risk. 8 chars = 4 billion combinations. Probability extremely low.
   - If collision occurs in practice, can increase hash length in future version.

2. **Symlink handling**: Should we resolve symlinks before hashing?
   - **Recommendation**: Yes, use `.resolve()` to follow symlinks.
   - Ensures same project accessed via different symlinks gets same hash.

3. **Project name conflicts**: What if sanitized name is empty string?
   - **Recommendation**: Fall back to "project" or "untitled" if sanitization results in empty.

## Success Metrics

- All acceptance criteria met
- Test coverage ≥95%
- No failing tests
- Code passes linting (if applicable)
- Documented with docstrings
- Ready for Task 1.2 to begin
