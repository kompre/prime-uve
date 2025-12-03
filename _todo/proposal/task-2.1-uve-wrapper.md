# Task 2.1: Implement uve Wrapper

**Parent Task**: Architecture Design for prime-uve CLI Tool
**Phase**: 2 - uve Wrapper (Quick Win)
**Status**: Proposal
**Dependencies**:
- Task 1.1 (Path Hashing System) ✅
- Task 1.3 (.env.uve File Management) ✅

## Objective

Implement the `uve` command - a lightweight, transparent wrapper that injects `.env.uve` into any `uv` command. This provides the core value proposition: seamless external venv support without requiring users to manually specify `--env-file` on every command.

## Context

The `uve` wrapper is designed to be:
- **Transparent**: Users type `uve` instead of `uv`, everything else is identical
- **Zero-config**: Automatically finds and uses `.env.uve` from the project
- **Cross-platform**: Ensures `HOME` environment variable is set on Windows
- **Pass-through**: All arguments, stdin/stdout/stderr, and exit codes forwarded to `uv`

This is a "quick win" because it:
- Provides immediate user value (external venv without manual flags)
- Is simple to implement (~50 lines of code)
- Has minimal dependencies (only Task 1.3's `find_env_file()`)
- Unlocks manual testing of the Phase 1 infrastructure

## Deliverables

### 1. Core Module: `src/prime_uve/uve/wrapper.py`

#### Main Entry Point

```python
def main() -> None:
    """Main entry point for uve command.

    Wraps uv commands with automatic .env.uve injection.

    Usage:
        uve add requests       → uv run --env-file .env.uve -- uv add requests
        uve sync               → uv run --env-file .env.uve -- uv sync
        uve run python app.py  → uv run --env-file .env.uve -- uv run python app.py
    """
```

#### Implementation Pseudocode

```python
def main() -> None:
    import subprocess
    import sys
    import os
    from pathlib import Path
    from prime_uve.core.env_file import find_env_file

    # 1. Find .env.uve file
    try:
        env_file = find_env_file()
    except Exception as e:
        print(f"Error finding .env.uve: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Ensure HOME is set on Windows
    env = os.environ.copy()
    if sys.platform == 'win32' and 'HOME' not in env:
        env['HOME'] = env.get('USERPROFILE', os.path.expanduser('~'))

    # 3. Build command: uv run --env-file .env.uve -- uv [args...]
    args = sys.argv[1:]  # All args after 'uve'
    cmd = ["uv", "run", "--env-file", str(env_file), "--", "uv"] + args

    # 4. Check if uv is available
    if not is_uv_available():
        print("Error: 'uv' command not found. Please install uv first.", file=sys.stderr)
        print("Visit: https://github.com/astral-sh/uv", file=sys.stderr)
        sys.exit(1)

    # 5. Run uv subprocess and forward exit code
    try:
        result = subprocess.run(cmd, env=env)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        print(f"Error running uv: {e}", file=sys.stderr)
        sys.exit(1)
```

#### Helper Function

```python
def is_uv_available() -> bool:
    """Check if uv command is available in PATH.

    Returns:
        True if uv is found, False otherwise
    """
    import shutil
    return shutil.which("uv") is not None
```

### 2. Package Structure Updates

```
src/
  prime_uve/
    uve/
      __init__.py            # Create package
      __main__.py            # Entry point: python -m prime_uve.uve
      wrapper.py             # Main implementation
```

**`src/prime_uve/uve/__init__.py`**:
```python
"""uve wrapper - transparent uv command wrapper with .env.uve injection."""

from .wrapper import main

__all__ = ["main"]
```

**`src/prime_uve/uve/__main__.py`**:
```python
"""Entry point for python -m prime_uve.uve."""

from .wrapper import main

if __name__ == "__main__":
    main()
```

### 3. Entry Point Configuration

Update `pyproject.toml`:
```toml
[project.scripts]
uve = "prime_uve.uve.wrapper:main"
prime-uve = "prime_uve.cli.main:main"  # For Phase 3
```

### 4. Unit Tests: `tests/test_uve_wrapper.py`

#### Basic Functionality Tests
```python
def test_main_finds_env_file(tmp_path, monkeypatch):
    """uve finds .env.uve in current directory."""

def test_main_passes_args_to_uv(tmp_path, monkeypatch):
    """Arguments are passed through to uv."""

def test_main_forwards_exit_code(tmp_path, monkeypatch):
    """Exit code from uv is forwarded."""

def test_main_sets_home_on_windows(tmp_path, monkeypatch):
    """On Windows, HOME is set if missing."""

def test_main_preserves_existing_home(tmp_path, monkeypatch):
    """Existing HOME variable is not overridden."""

def test_is_uv_available_true(monkeypatch):
    """Detects when uv is available."""

def test_is_uv_available_false(monkeypatch):
    """Detects when uv is not available."""

def test_main_uv_not_found(tmp_path, monkeypatch, capsys):
    """Clear error when uv not found."""
```

#### Command Construction Tests
```python
def test_main_constructs_correct_command(tmp_path, monkeypatch):
    """Verify exact command: uv run --env-file .env.uve -- uv [args]."""

def test_main_with_no_args(tmp_path, monkeypatch):
    """Works with no arguments (uve → uv run --env-file .env.uve -- uv)."""

def test_main_with_multiple_args(tmp_path, monkeypatch):
    """Works with multiple arguments."""

def test_main_with_flags(tmp_path, monkeypatch):
    """Preserves flags like --verbose."""

def test_main_with_quoted_args(tmp_path, monkeypatch):
    """Handles quoted arguments correctly."""
```

#### Environment Variable Tests
```python
def test_main_does_not_expand_env_file_vars(tmp_path, monkeypatch):
    """Variables in .env.uve are NOT expanded by uve (left to uv)."""

def test_main_windows_home_from_userprofile(tmp_path, monkeypatch):
    """On Windows, HOME set from USERPROFILE if missing."""

def test_main_windows_home_fallback(tmp_path, monkeypatch):
    """On Windows, falls back to expanduser if USERPROFILE missing."""

def test_main_unix_no_home_modification(tmp_path, monkeypatch):
    """On Unix, HOME is not modified."""
```

#### Error Handling Tests
```python
def test_main_env_file_not_found_error(tmp_path, monkeypatch, capsys):
    """Error when .env.uve cannot be found/created."""

def test_main_subprocess_error(tmp_path, monkeypatch, capsys):
    """Handles subprocess errors gracefully."""

def test_main_keyboard_interrupt(tmp_path, monkeypatch):
    """Handles Ctrl+C (KeyboardInterrupt) gracefully."""

def test_main_uv_command_fails(tmp_path, monkeypatch):
    """Forwards non-zero exit code from uv."""
```

#### Integration Tests
```python
def test_main_with_empty_env_file(tmp_path, monkeypatch):
    """Works with empty .env.uve file."""

def test_main_with_comments_only(tmp_path, monkeypatch):
    """Works with .env.uve containing only comments."""

def test_main_full_workflow(tmp_path, monkeypatch):
    """Full workflow: find env file, set HOME, run uv."""
```

### 5. Manual Testing Guide

Create `tests/manual/test_uve_wrapper_manual.md`:

```markdown
# Manual Testing Guide for uve Wrapper

## Prerequisites
- uv installed and in PATH
- prime-uve installed in development mode: `uv tool install -e .`

## Test Cases

### 1. Basic Commands
```bash
cd /path/to/test-project
echo 'UV_PROJECT_ENVIRONMENT=${HOME}/prime-uve/venvs/test_12345678' > .env.uve

# Test basic command
uve sync

# Test command with args
uve add requests

# Test run command
uve run python -c "print('Hello from uve')"
```

### 2. Cross-Platform HOME Variable
**Windows**:
```powershell
# Remove HOME if set
$env:HOME = $null
uve run python -c "import os; print(os.environ.get('HOME'))"
# Should print: C:\Users\<username>
```

**Linux/macOS**:
```bash
uve run python -c "import os; print(os.environ.get('HOME'))"
# Should print: /home/<username>
```

### 3. Variable Preservation
```bash
# Create .env.uve with ${HOME}
echo 'UV_PROJECT_ENVIRONMENT=${HOME}/prime-uve/venvs/test_12345678' > .env.uve

# Verify uv receives unexpanded variable
uve run python -c "import os; print(os.environ.get('UV_PROJECT_ENVIRONMENT'))"
# Should show expanded path (uv expanded it, not uve)
```

### 4. Error Cases
```bash
# No .env.uve
rm .env.uve
uve sync  # Should create .env.uve or use default

# uv not in PATH
# Temporarily rename uv
mv $(which uv) $(which uv).bak
uve sync  # Should show clear error
mv $(which uv).bak $(which uv)
```

### 5. Exit Code Forwarding
```bash
# Command that fails
uve run python -c "import sys; sys.exit(42)"
echo $?  # Should be 42

# Command that succeeds
uve run python -c "print('success')"
echo $?  # Should be 0
```
```

## Implementation Plan

### Step 1: Create Package Structure
1. Create `src/prime_uve/uve/` directory
2. Create `__init__.py`, `__main__.py`, `wrapper.py`
3. Add entry point to `pyproject.toml`

### Step 2: Implement Core Wrapper
1. Implement `main()` function with subprocess call
2. Implement `is_uv_available()` helper
3. Add HOME environment variable handling for Windows
4. Add error handling (uv not found, subprocess errors)

### Step 3: Write Unit Tests
1. Mock `subprocess.run()` in tests
2. Mock `find_env_file()` to return test paths
3. Test command construction
4. Test environment variable handling
5. Test error cases

### Step 4: Manual Testing
1. Install in development mode: `uv tool install -e .`
2. Test basic commands (sync, add, run)
3. Test on Windows and Linux (cross-platform)
4. Test variable preservation
5. Test error cases

### Step 5: Documentation
1. Update README with uve usage examples
2. Create manual testing guide
3. Document common issues and troubleshooting

## Acceptance Criteria

- ✅ `uve` command is installed and available after `uv tool install`
- ✅ `find_env_file()` is called to locate `.env.uve`
- ✅ All arguments passed to `uve` are forwarded to `uv`
- ✅ Exit code from `uv` subprocess is forwarded correctly
- ✅ Works with empty `.env.uve` files (uv handles gracefully)
- ✅ On Windows, `HOME` environment variable is set if missing
- ✅ `HOME` is set from `USERPROFILE` on Windows
- ✅ Existing `HOME` variable is not overridden
- ✅ Variables in `.env.uve` are NOT expanded by uve (left to uv)
- ✅ Clear error message when `uv` command not found
- ✅ Handles `KeyboardInterrupt` (Ctrl+C) gracefully
- ✅ All unit tests pass (>95% coverage)
- ✅ Manual testing passes on both Windows and Linux
- ✅ Same `.env.uve` file works on both platforms

## Example Usage

### User Workflow

**Before (manual --env-file every time)**:
```bash
uv run --env-file .env.uve -- uv add requests
uv run --env-file .env.uve -- uv sync
uv run --env-file .env.uve -- uv run python app.py
```

**After (transparent with uve)**:
```bash
uve add requests
uve sync
uve run python app.py
```

### What Happens Under the Hood

```bash
# User types:
uve add requests

# uve does:
1. Find .env.uve (walks up to project root)
2. Set HOME=USERPROFILE on Windows (if needed)
3. Run: uv run --env-file .env.uve -- uv add requests
4. Forward exit code
```

## Dependencies on Other Tasks

**This task depends on**:
- Task 1.3: .env.uve File Management ✅ (uses `find_env_file()`)

**This task blocks**:
- Manual testing of Phase 1 infrastructure
- User adoption (provides immediate value)

**This task does NOT block**:
- Phase 3 CLI commands (independent work streams)

## Testing Strategy

### Unit Tests (with mocking)
- Mock `subprocess.run()` to avoid calling real `uv`
- Mock `find_env_file()` to return test paths
- Mock `shutil.which()` to simulate uv availability
- Test all code paths and error conditions

### Integration Tests
- Create real `.env.uve` files in temp directories
- Mock `subprocess.run()` but test full workflow
- Verify command construction and environment setup

### Manual Tests
- Install in development mode
- Test with real `uv` commands
- Test on both Windows and Linux
- Verify cross-platform compatibility

## Edge Cases to Handle

1. **No .env.uve**: `find_env_file()` creates one, uve uses it
2. **Empty .env.uve**: uv handles gracefully (no variables to load)
3. **uv not in PATH**: Show clear error with installation instructions
4. **Subprocess error**: Forward error and exit code
5. **KeyboardInterrupt**: Exit cleanly with code 130
6. **No HOME or USERPROFILE**: Fall back to `os.path.expanduser('~')`
7. **Malformed .env.uve**: uv will error, uve forwards the error
8. **Spaces in paths**: Use list form of subprocess.run() (handles automatically)
9. **Special characters in args**: Subprocess handles correctly
10. **stdin/stdout/stderr**: subprocess.run() forwards by default

## Open Questions

1. **Should uve validate .env.uve before passing to uv?**
   - **Decision**: No. Let uv handle validation and show its own errors. Keep uve simple.

2. **Should uve have a --help flag?**
   - **Decision**: No. `uve --help` forwards to `uv --help`. Keep transparent.

3. **Should uve have a --version flag?**
   - **Decision**: No for v1. Can add `uve --uve-version` later if needed.

4. **What if user has .env.uve but wants to skip it?**
   - **Decision**: Use `uv` directly (not `uve`). Keep uve simple.

5. **Should uve support UVE_DISABLE environment variable?**
   - **Decision**: Not in v1. Can add later if users request it.

## Success Metrics

- All acceptance criteria met
- Test coverage >95%
- Manual testing passes on Windows and Linux
- User can immediately use uve instead of uv
- No complaints about cross-platform compatibility
- Zero performance overhead (subprocess is fast)

## Notes

- This is intentionally simple: ~50 lines of actual code
- Main value: convenience (don't type --env-file every time)
- Secondary value: ensures HOME is set on Windows
- Enables dogfooding: developers can use uve to test Phase 1 infrastructure
- Does NOT implement any venv management (that's Phase 3)
- Does NOT parse or modify .env.uve (just passes path to uv)
