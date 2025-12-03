# Architecture Design for prime-uve CLI Tool

## Original Objective

Define the architecture for the prime-uve CLI tool as described in README.md. Define the overarching method then break it down into smaller tasks with clear objectives and deliverables.

## Primary Use Case

**Multi-User Network Share Scenario**:
- Project repository stored on network share (accessible by multiple users/machines)
- Each user needs their own local venv (no interference between users)
- Same `.env.uve` file checked into git works for everyone
- Variables like `${HOME}` expand to each user's local home directory
- `uv` handles variable expansion natively at runtime

This design ensures that:
1. `.env.uve` can be committed to version control
2. Each user gets isolated venv on their local machine
3. No manual configuration per user required
4. Works seamlessly across Windows, macOS, Linux

## High-Level Architecture

### Two CLI Tools

1. **`uve`** - Lightweight wrapper that transparently injects `.env.uve` into any `uv` command
   ```bash
   uve add package  # → uv run --env-file .env.uve -- uv add package
   ```

2. **`prime-uve`** - Full-featured venv management tool with subcommands
   ```bash
   prime-uve init
   prime-uve list
   prime-uve prune --orphan
   ```

### Core Components

```
prime-uve/
├── uve wrapper          # Finds .env.uve, wraps uv commands
├── cache system         # Tracks project → venv mappings
├── path generator       # Creates deterministic venv paths with hashing
├── env file manager     # Reads/writes/searches for .env.uve
└── CLI commands         # init, list, prune, activate, configure
```

## Detailed Design

### 1. Cache System

**Purpose**: Track all managed venvs to support validation and cleanup.

**Storage Location**: `$HOME/.prime-uve/cache.json`

**Schema**:
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

**Notes**:
- `venv_path` always uses `${HOME}` (cross-platform)
- `venv_path_expanded` is platform-specific, for local validation only
- Same `venv_path` value works on Windows, macOS, Linux

**Operations**:
- `add_mapping(project_path, venv_path)` - Register new venv
- `get_mapping(project_path)` - Retrieve venv for project
- `remove_mapping(project_path)` - Remove from cache
- `list_all()` - Return all mappings
- `validate_mapping(project_path)` - Check if project/venv/env-file still exist and match

**Locking**: Use file locking for concurrent access safety.

### 2. Path Generation and Hashing

**Venv Path Format**: `${HOME}/prime-uve/venvs/{project_name}_{hash}`

Where:
- **Always use `${HOME}`** (cross-platform compatibility - works on Windows, macOS, Linux)
- `project_name` = from `pyproject.toml` name field, or parent directory name if no pyproject
- `hash` = first 8 characters of SHA256(normalized_absolute_project_path)

**Example path in .env.uve** (same on all platforms):
```bash
UV_PROJECT_ENVIRONMENT=${HOME}/prime-uve/venvs/myproject_a1b2c3d4
```

**Windows Compatibility**: `uve` wrapper ensures `HOME` environment variable is set on Windows:
- If already set (Git Bash, WSL, modern PowerShell): use it
- If not set: set `HOME=%USERPROFILE%` before calling uv

**Hash Algorithm**:
```python
import hashlib
from pathlib import Path

def generate_hash(project_path: Path) -> str:
    normalized = project_path.resolve().as_posix()  # Cross-platform
    return hashlib.sha256(normalized.encode()).hexdigest()[:8]
```

**Project Name Extraction**:
1. Try to read `pyproject.toml` and get `project.name`
2. If not found or invalid, use parent directory name
3. Sanitize name (lowercase, replace non-alphanumeric with `-`)

### 3. .env.uve Lookup Logic

**Search Algorithm**:
```python
def find_env_file(start_path: Path = None) -> Path | None:
    current = start_path or Path.cwd()

    # Step 1: Check current directory
    if (current / ".env.uve").exists():
        return current / ".env.uve"

    # Step 2: Walk up to project root
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            # Found project root
            if (current / ".env.uve").exists():
                return current / ".env.uve"
            else:
                # Step 3: Create default empty file at root
                env_file = current / ".env.uve"
                env_file.touch()
                return env_file
        current = current.parent

    # No project root found - create in original start location
    env_file = (start_path or Path.cwd()) / ".env.uve"
    env_file.touch()
    return env_file
```

**File Format**:
```bash
# .env.uve - SAME on all platforms (Windows, macOS, Linux)
UV_PROJECT_ENVIRONMENT=${HOME}/prime-uve/venvs/myproject_a1b2c3d4
```

**Critical Design Constraint**: The path MUST use expandable variables (not absolute paths) to support the primary use case:
- Project stored on network share
- Multiple users/machines/platforms access same project
- Each user gets their own local venv (no interference)
- Same `.env.uve` file works for all users on all platforms because `${HOME}` is universal

**Variable Expansion**:
- `uv` handles variable expansion natively
- `${HOME}` works on Unix/macOS/Linux natively
- On Windows, `uve` wrapper ensures `HOME` is set (to `%USERPROFILE%`) before calling uv

### 4. uve Wrapper Implementation

**Behavior**:
1. Find `.env.uve` using lookup logic
2. If file exists and has content, prepend `uv run --env-file .env.uve --`
3. Pass through all CLI arguments to `uv`
4. Forward exit code from `uv` process

**Implementation**:
```python
def main():
    import subprocess
    import sys
    import os

    env_file = find_env_file()
    args = sys.argv[1:]  # Get all args after 'uve'

    # Ensure HOME is set on Windows for cross-platform compatibility
    env = os.environ.copy()
    if sys.platform == 'win32' and 'HOME' not in env:
        env['HOME'] = env.get('USERPROFILE', os.path.expanduser('~'))

    # Always use --env-file, uv handles empty files correctly
    cmd = ["uv", "run", "--env-file", str(env_file), "--", "uv"] + args

    sys.exit(subprocess.run(cmd, env=env).returncode)
```

**Edge Cases**:
- Empty `.env.uve` → uv handles correctly, no special logic needed
- `.env.uve` with comments only → uv handles correctly
- Malformed `.env.uve` → fail with error (users explicitly using `uve` expect `.env.uve` to be loaded)

### 5. prime-uve CLI Structure

**Framework**: Use `click` for CLI (simple, well-documented, standard)

**Command Structure**:
```
prime-uve
├── init              Initialize project with external venv
├── list              List all managed venvs with validation
├── prune             Clean up venvs
│   ├── --all        Remove all venvs
│   ├── --orphan     Remove orphaned venvs only
│   ├── --current    Remove current project's venv
│   └── [path]       Remove specific venv by path
├── activate          Print activation command for current venv
└── configure
    └── vscode        Update .code-workspace with venv path
```

### 6. Subcommand Specifications

#### 6.1 `prime-uve init`

**Purpose**: Set up external venv for current project.

**Steps**:
1. Detect project root (find `pyproject.toml`)
2. Check if already initialized (`.env.uve` exists with content)
3. Generate venv path using hash algorithm
4. Create `.env.uve` with `UV_PROJECT_ENVIRONMENT=<path>`
5. Add mapping to cache
6. Create venv directory structure
7. Run `uv sync` to initialize venv

**Options**:
- `--force` - Reinitialize even if already set up
- `--venv-dir` - Override default venv directory location

**Output**:
```
✓ Project: myproject
✓ Venv path: ${HOME}/prime-uve/venvs/myproject_a1b2c3d4
✓ Created .env.uve
✓ Initialized venv at /home/username/prime-uve/venvs/myproject_a1b2c3d4
```

Note: Shows both the variable form (what's stored) and expanded form (where venv actually is).

#### 6.2 `prime-uve list`

**Purpose**: Show all tracked venvs with validation status.

**Steps**:
1. Read cache
2. For each mapping, validate:
   - Project directory exists
   - Venv directory exists
   - `.env.uve` exists and contains matching path
3. Display table with status

**Output Format**:
```
PROJECT                 VENV                          STATUS
myproject               ~/prime-uve/venvs/mypr...     ✓ Valid
old-project             ~/prime-uve/venvs/oldpr...    ✗ Project deleted
another-project         ~/prime-uve/venvs/anoth...    ⚠ Path mismatch
```

**Options**:
- `--json` - Output as JSON
- `--orphan-only` - Show only orphaned venvs

#### 6.3 `prime-uve prune`

**Purpose**: Clean up venv directories.

**Modes**:

**`prune --all`**:
- Remove all venv directories in `~/prime-uve/venvs/`
- Clear entire cache
- Confirm with user (unless `--yes`)

**`prune --orphan`**:
- Run validation on all cached venvs
- Remove venvs where:
  - Project directory doesn't exist
  - `.env.uve` missing or path doesn't match cache
- Remove from cache
- Keep venvs for valid projects

**`prune --current`**:
- Find current project's venv from cache
- Remove venv directory
- Remove from cache
- Clear `.env.uve`

**`prune <path>`**:
- Remove venv at specific path
- Remove from cache if tracked
- Validate path is within prime-uve directory

**Safety**:
- Always show what will be deleted and ask for confirmation
- `--yes` flag to skip confirmation
- `--dry-run` to show what would be deleted

#### 6.4 `prime-uve activate`

**Purpose**: Output activation command for current project's venv and export all variables from `.env.uve`.

**Behavior**:
1. Find `.env.uve` in current project
2. Parse `UV_PROJECT_ENVIRONMENT` path and expand variables
3. Parse all other variables in `.env.uve` for export
4. Detect shell (bash, zsh, fish, powershell)
5. Output commands to:
   - Export all `.env.uve` variables
   - Activate the venv

**Output Examples**:
```bash
# Bash/Zsh - exports all .env.uve vars, then activates
export UV_PROJECT_ENVIRONMENT="${HOME}/prime-uve/venvs/myproject_a1b2c3d4"
export OTHER_VAR="value"
source /home/user/prime-uve/venvs/myproject_a1b2c3d4/bin/activate

# Fish
set -x UV_PROJECT_ENVIRONMENT "$HOME/prime-uve/venvs/myproject_a1b2c3d4"
set -x OTHER_VAR "value"
source /home/user/prime-uve/venvs/myproject_a1b2c3d4/bin/activate.fish

# PowerShell - uses ${HOME} (not ${env:USERPROFILE}) for cross-platform compatibility
$env:HOME = $env:USERPROFILE  # Ensure HOME is set
$env:UV_PROJECT_ENVIRONMENT="${HOME}/prime-uve/venvs/myproject_a1b2c3d4"
$env:OTHER_VAR="value"
& C:\Users\user\prime-uve\venvs\myproject_a1b2c3d4\Scripts\Activate.ps1
```

**Usage**:
```bash
eval "$(prime-uve activate)"
```

**Options**:
- `--shell <name>` - Override shell detection

#### 6.5 `prime-uve configure vscode`

**Purpose**: Update VS Code workspace settings with venv path.

**Steps**:
1. Find `.env.uve` and parse venv path
2. Find or create `.code-workspace` file in project root
3. Update `settings.python.defaultInterpreterPath`
4. Preserve other workspace settings

**Workspace File Update**:
```json
{
  "folders": [{"path": "."}],
  "settings": {
    "python.defaultInterpreterPath": "/home/user/prime-uve/venvs/myproject_a1b2c3d4/bin/python"
  }
}
```

**Edge Cases**:
- Multiple `.code-workspace` files → ask user which to update
- No workspace file → offer to create one
- Existing interpreter setting → ask to overwrite

### 7. Project Structure

```
src/
  prime_uve/
    __init__.py
    __main__.py              # Entry point for 'prime-uve' command

    cli/
      __init__.py
      main.py                # Click app and command group
      init.py                # init command
      list.py                # list command
      prune.py               # prune command
      activate.py            # activate command
      configure.py           # configure vscode command

    core/
      __init__.py
      cache.py               # Cache operations (load, save, validate)
      paths.py               # Path generation and hashing
      env_file.py            # .env.uve search and manipulation
      venv.py                # Venv creation and management
      project.py             # Project detection and metadata

    uve/
      __init__.py
      wrapper.py             # uve wrapper implementation
      __main__.py            # Entry point for 'uve' command

    utils/
      __init__.py
      shell.py               # Shell detection
      validators.py          # Path and config validation

tests/
  test_cache.py
  test_paths.py
  test_env_file.py
  test_cli/
    test_init.py
    test_list.py
    test_prune.py
  test_uve/
    test_wrapper.py
```

### 8. Entry Points Configuration

**In `pyproject.toml`**:
```toml
[project.scripts]
prime-uve = "prime_uve.cli.main:main"
uve = "prime_uve.uve.wrapper:main"
```

### 9. Cross-Platform Considerations

**Path Format in .env.uve**:
- **MUST use expandable variables** (not absolute paths) to support multi-user/multi-machine/multi-platform scenarios
- **Always use `${HOME}`** regardless of platform (cross-platform compatibility)
- Let `uv` handle variable expansion at runtime
- DO NOT expand variables when writing to `.env.uve`
- DO NOT use `.resolve()` on paths with variables (would expand them)
- `uve` wrapper ensures `HOME` is set on Windows before calling uv

**Path Operations in Code**:
- Use `pathlib.Path` for all path operations
- Only expand variables when needed for validation (check if venv exists locally)
- Use `.resolve()` only for project paths when hashing (not for venv paths in .env.uve)

**Shell Integration**:
- Detect shell from `$SHELL` env var or `COMSPEC` on Windows
- Provide activation scripts for bash, zsh, fish, PowerShell

**Testing**:
- Test `${HOME}` variable expansion works correctly on Windows, macOS, Linux
- Test network share scenario: same `.env.uve` creates local venvs per user
- **Test cross-platform scenario**: Project initialized on Windows, accessed on Linux (and vice versa)
- Verify `uve` wrapper sets `HOME` on Windows when not present
- Verify `HOME` resolves to correct user directory on all platforms

### 10. Error Handling

**User-Facing Errors**:
- Clear, actionable error messages
- Exit codes: 0 (success), 1 (user error), 2 (system error)
- Colored output for warnings/errors (use `click.style`)

**Common Error Scenarios**:
- Not in a Python project (no `pyproject.toml`) → guide user
- Venv path already exists but not tracked → offer to import
- Cache corrupted → offer to rebuild from existing `.env.uve` files
- Permission denied → explain and suggest fixes

### 11. Testing Strategy

**Unit Tests**:
- Test cache operations with temporary files
- Test path hashing determinism
- Test .env.uve lookup logic with mock filesystem
- Test each CLI command with click's test runner

**Integration Tests**:
- Create temporary projects with `pyproject.toml`
- Test full workflow: init → list → prune
- Test uve wrapper with mock uv command
- Test cross-platform path handling

**Manual Tests**:
- Install with `uv tool install`
- Test on Windows, macOS, Linux
- Test shell activation in different shells
- Test VS Code workspace configuration

## Task Breakdown

### Phase 1: Core Infrastructure (Foundation)

#### Task 1.1: Implement Path Hashing System
**Objective**: Create deterministic, collision-resistant path hashing and cross-platform variable-based path generation.

**Deliverables**:
- `src/prime_uve/core/paths.py` with:
  - `generate_hash(project_path: Path) -> str`
  - `generate_venv_path(project_path: Path) -> str` - Always returns path with `${HOME}` (cross-platform)
  - `expand_path_variables(path: str) -> Path` - Expands `${HOME}` to actual path for local operations
  - `get_project_name(project_path: Path) -> str`
  - `ensure_home_set()` - Ensures HOME env var is set (for Windows compatibility)
- Unit tests covering edge cases (special chars, long paths, symlinks, variable expansion)

**Acceptance Criteria**:
- Same project path always generates same hash
- Different paths generate different hashes (collision resistance)
- Works on Windows, macOS, Linux paths
- Project name sanitization handles special characters
- **Generated paths ALWAYS use `${HOME}`** (never platform-specific variables)
- Variable expansion correctly resolves `${HOME}` on all platforms
- On Windows, `${HOME}` expansion uses `USERPROFILE` or user directory

---

#### Task 1.2: Implement Cache System
**Objective**: Persistent storage for project → venv mappings.

**Deliverables**:
- `src/prime_uve/core/cache.py` with:
  - `Cache` class with add, get, remove, list, validate methods
  - File locking for concurrent access
  - Auto-migration for cache version changes
- Unit tests with temporary cache files

**Acceptance Criteria**:
- Cache persists across program invocations
- Concurrent access doesn't corrupt cache
- Validation correctly identifies orphaned venvs
- Invalid cache files are handled gracefully

---

#### Task 1.3: Implement .env.uve Lookup Logic
**Objective**: Search algorithm for finding/creating .env.uve files, with variable-aware parsing.

**Deliverables**:
- `src/prime_uve/core/env_file.py` with:
  - `find_env_file(start_path: Path) -> Path`
  - `read_env_file(path: Path) -> dict` - Returns raw values with variables intact
  - `write_env_file(path: Path, vars: dict)` - Writes variables without expanding them
  - `get_venv_path_from_env(env_dict: dict, expand: bool = False) -> str | Path` - Get venv path, optionally expanded
- Unit tests with mock directory structures

**Acceptance Criteria**:
- Correctly walks up directory tree to project root
- Creates file at project root if missing
- Handles edge cases (root of filesystem, no pyproject.toml)
- Parses .env format correctly
- Preserves variables when reading/writing (doesn't expand them)
- Can optionally expand variables for local validation

---

#### Task 1.4: Implement Project Detection
**Objective**: Find project root and extract metadata.

**Deliverables**:
- `src/prime_uve/core/project.py` with:
  - `find_project_root(start_path: Path) -> Path | None`
  - `get_project_metadata(project_path: Path) -> dict`
- Unit tests

**Acceptance Criteria**:
- Finds project root by locating pyproject.toml
- Extracts project name from pyproject.toml
- Falls back to directory name if no pyproject.toml
- Handles malformed pyproject.toml files

---

### Phase 2: uve Wrapper (Quick Win)

#### Task 2.1: Implement uve Wrapper
**Objective**: Simple wrapper that injects .env.uve into uv commands with cross-platform HOME support.

**Deliverables**:
- `src/prime_uve/uve/wrapper.py` with main entry point
- Cross-platform HOME environment variable handling
- Integration test that mocks uv subprocess
- Manual testing with real uv commands on Windows and Linux
- Test that variables are passed through (not expanded by uve)

**Acceptance Criteria**:
- Finds .env.uve correctly
- Passes all arguments through to uv
- Forwards exit code from uv
- Works with empty .env.uve files
- **On Windows: ensures HOME is set before calling uv** (set to USERPROFILE if missing)
- Does NOT expand variables in .env.uve (leaves that to uv)
- Error handling for missing uv binary
- Fails clearly on malformed .env.uve
- **Same .env.uve works when accessed from Windows and Linux**

---

### Phase 3: CLI Commands (Core Features)

#### Task 3.1: CLI Framework Setup
**Objective**: Set up Click CLI structure and common utilities.

**Deliverables**:
- `src/prime_uve/cli/main.py` with Click group
- Common options (--verbose, --yes, --dry-run)
- Error handling and output formatting
- Version command

**Acceptance Criteria**:
- `prime-uve --help` shows all commands
- `prime-uve --version` shows version from pyproject.toml
- Colored output for errors/warnings/success
- Consistent error message format

---

#### Task 3.2: Implement `prime-uve init`
**Objective**: Initialize project with external venv.

**Deliverables**:
- `src/prime_uve/cli/init.py`
- Creates .env.uve with generated venv path
- Adds to cache
- Creates venv directory
- Unit and integration tests

**Acceptance Criteria**:
- Detects if already initialized
- Generates correct venv path
- Creates functional .env.uve
- Updates cache correctly
- `--force` flag re-initializes
- Clear error if not in a project

---

#### Task 3.3: Implement `prime-uve list`
**Objective**: Display all managed venvs with validation.

**Deliverables**:
- `src/prime_uve/cli/list.py`
- Table output with validation status
- `--json` output option
- `--orphan-only` filter
- Unit tests

**Acceptance Criteria**:
- Shows all cached venvs
- Validation status is accurate (✓/✗/⚠)
- JSON output is valid and machine-readable
- Performance is acceptable with 100+ venvs
- Empty cache shows helpful message

---

#### Task 3.4: Implement `prime-uve prune`
**Objective**: Clean up venv directories.

**Deliverables**:
- `src/prime_uve/cli/prune.py`
- All four modes: --all, --orphan, --current, path
- Confirmation prompts
- `--dry-run` support
- Unit and integration tests

**Acceptance Criteria**:
- Correctly identifies orphaned venvs
- Shows what will be deleted before deleting
- `--yes` skips confirmation
- `--dry-run` doesn't delete anything
- Safely handles errors during deletion
- Updates cache after deletion

---

#### Task 3.5: Implement `prime-uve activate`
**Objective**: Output activation command for current venv and export all .env.uve variables.

**Deliverables**:
- `src/prime_uve/cli/activate.py`
- `src/prime_uve/utils/shell.py` for shell detection
- Support for bash, zsh, fish, PowerShell
- Unit tests

**Acceptance Criteria**:
- Detects shell correctly
- Outputs export commands for ALL variables in .env.uve (not just UV_PROJECT_ENVIRONMENT)
- Outputs correct activation command for each shell
- Expands variables in activation path (but exports them with variables intact for env vars)
- Works with `eval "$(prime-uve activate)"`
- Handles missing .env.uve gracefully
- `--shell` override works

---

#### Task 3.6: Implement `prime-uve configure vscode`
**Objective**: Update VS Code workspace with venv path.

**Deliverables**:
- `src/prime_uve/cli/configure.py`
- Parses and updates .code-workspace JSON
- Creates workspace file if needed
- Unit tests

**Acceptance Criteria**:
- Correctly updates python.defaultInterpreterPath
- Preserves other workspace settings
- Handles missing workspace file
- Asks before overwriting existing interpreter setting
- Creates valid JSON output

---

### Phase 4: Polish and Release

#### Task 4.1: Comprehensive Testing
**Objective**: Ensure robustness across platforms and scenarios, especially network share use case.

**Deliverables**:
- Integration test suite covering full workflows
- Manual testing on Windows, macOS, Linux
- Edge case testing (symlinks, long paths, special characters)
- Performance testing with many venvs
- **Network share scenario testing**: Mock multiple users accessing same project

**Acceptance Criteria**:
- All unit tests pass
- Integration tests cover main workflows
- Tested on Windows 10/11, macOS, Ubuntu
- No crashes on edge cases
- Performance is acceptable
- **Verified**: Same `.env.uve` with variables works for multiple users
- **Verified**: Variable expansion creates separate local venvs per user

---

#### Task 4.2: Documentation
**Objective**: User-facing documentation.

**Deliverables**:
- Update README.md with usage examples
- Add docstrings to all public functions
- Create CONTRIBUTING.md if needed
- Add error message documentation

**Acceptance Criteria**:
- README has clear install and usage instructions
- Examples for each command
- Troubleshooting section
- API documentation for library use (if applicable)

---

#### Task 4.3: Package and Release
**Objective**: Make installable via `uv tool install`.

**Deliverables**:
- Correct entry points in pyproject.toml
- Build wheel with `uv build`
- Test installation with `uv tool install`
- Tag release in git

**Acceptance Criteria**:
- `uv tool install prime-uve` works
- Both `uve` and `prime-uve` commands available after install
- Works in isolated environment
- Version number follows semver

---

## Risk Assessment

**High Risk**:
- Path hashing collisions (mitigated by using SHA256)
- Cross-platform path handling (test extensively)
- Cache corruption from concurrent access (use file locking)

**Medium Risk**:
- Shell detection inaccuracy (provide manual override)
- VS Code workspace format changes (test with current version)
- UV command changes (wrap carefully, forward everything)

**Low Risk**:
- Performance with many venvs (unlikely to have 1000+)
- Disk space (venvs are already large, external location helps)

## Open Questions

1. ~~**Should uve fail if .env.uve is malformed, or fall back to plain uv?**~~
   - **RESOLVED**: Fail with error. Users using `uve` explicitly expect `.env.uve` to be loaded.

2. **Should prime-uve init run uv sync automatically?**
   - Recommendation: Yes, for better UX (with --no-sync flag to skip)

3. **Should we support multiple venvs per project (e.g., for different Python versions)?**
   - Recommendation: Not in v1, keep simple. Can add later with suffix like `_py311`

4. **What if user manually moves project directory?**
   - Recommendation: Hash will differ, treated as new project. Document this behavior. (correct)

5. ~~**Should activate command modify shell directly or output command?**~~
   - **RESOLVED**: Output command for `eval`, safer and more transparent

6. ~~**Should we auto-detect platform and use ${HOME} vs ${USERPROFILE}, or let user specify?**~~
   - **RESOLVED**: Always use `${HOME}` for cross-platform compatibility (see below)

7. **Cross-platform variable problem**: What if project initialized on Windows (with `${USERPROFILE}`) is accessed on Linux?
   - **CRITICAL ISSUE**: Platform-specific variables break cross-platform sharing
   - **Solution**: Always use `${HOME}` in `.env.uve` regardless of platform
   - **Implementation**:
     - `prime-uve init` always writes `${HOME}` (never `${USERPROFILE}`)
     - On Windows, `uve` wrapper ensures `HOME` env var is set before calling uv
     - Most modern Windows setups have `HOME` set (Git Bash, WSL, modern PowerShell)
     - If not set, `uve` sets `HOME=%USERPROFILE%` before invoking uv
   - **Result**: Same `.env.uve` works on Windows, macOS, Linux without modification

## Success Criteria

- [ ] Both `uve` and `prime-uve` installable via `uv tool install`
- [ ] `uve` correctly wraps all uv commands with .env.uve
- [ ] All prime-uve subcommands implemented and tested
- [ ] Works on Windows, macOS, Linux
- [ ] Cache system is reliable and doesn't corrupt
- [ ] Clear error messages for common issues
- [ ] Documentation complete with examples
- [ ] No data loss in prune operations (safe by default)
- [ ] **Primary use case validated**: Same `.env.uve` on network share creates isolated local venvs for each user
- [ ] **Cross-platform compatibility**: Project initialized on Windows works on Linux and vice versa
- [ ] `${HOME}` variable correctly handled on all platforms (including Windows)
- [ ] `.env.uve` can be safely committed to git and works for all users

## Timeline Estimate

Not providing timeline - this is a complexity estimate:

- **Phase 1**: Core Infrastructure - 4 tasks, foundational work
- **Phase 2**: uve Wrapper - 1 task, quick win for basic functionality
- **Phase 3**: CLI Commands - 6 tasks, main feature development
- **Phase 4**: Polish - 3 tasks, finalization

Total: 14 discrete tasks with clear deliverables
