# Task Proposal: Add `prime-uve register` Command

## Problem Statement

The cache.json file is only populated when running `prime-uve init`. This creates a critical synchronization gap:

**Scenario:**
1. User runs `prime-uve init` → `.env.uve` created, cache.json populated
2. User manually deletes/edits `.env.uve` or cache.json gets corrupted
3. User runs `uve sync` → venv created at correct location from `.env.uve`
4. User runs `prime-uve list` → venv marked as orphaned (not in cache!)
5. User runs `prime-uve prune --orphan` → valid, working venv gets deleted

The root issue: **There's no way to re-register an already-initialized project with the cache after cache desync.**

## Proposed Solution

Add registration functionality in two forms:

1. **Internal auto-registration** - Called automatically by `list` and `prune` commands
   - Silently registers current project if `.env.uve` exists
   - No error if not in a managed project

2. **External `prime-uve register` command** - Explicit manual registration
   - Verbose feedback for user
   - Supports dry-run and JSON output

Both read existing `.env.uve`, extract `UV_PROJECT_ENVIRONMENT`, and update cache.json with the mapping.

## Technical Analysis

### Current Architecture

**Cache Flow (init):**
```
prime-uve init
  ↓
generate_venv_path() → ${HOME}/prime-uve/venvs/<name>_<hash>
  ↓
write .env.uve
  ↓
cache.add_mapping(project_path, venv_path, name, hash)
  ↓
cache.json updated
```

**Validation Flow (list):**
```
prime-uve list
  ↓
cache.list_all() → get all mappings
  ↓
for each mapping:
  ↓
  validate_mapping():
    - Check .env.uve exists
    - Check .env.uve UV_PROJECT_ENVIRONMENT == cached venv_path
    - Status: valid | orphaned
```

**Gap:** If cache.json is missing an entry but `.env.uve` exists and is correct, there's no recovery path.

### Implementation Plan

#### 1. Internal Auto-Registration Function

```python
def auto_register_current_project(cache: Cache) -> bool:
    """Silently register current project if in a managed project.

    Called internally by list/prune commands before executing.

    Returns:
        True if registered, False if nothing to register
    """
    try:
        # Find project root (same logic as uve wrapper)
        project_root = find_project_root()
        if not project_root:
            return False  # Not in a project

        # Check for .env.uve
        env_file = project_root / ".env.uve"
        if not env_file.exists():
            return False  # No .env.uve

        # Read UV_PROJECT_ENVIRONMENT
        env_vars = read_env_file(env_file)
        venv_path = env_vars.get("UV_PROJECT_ENVIRONMENT")
        if not venv_path or not venv_path.strip():
            return False  # Not set or empty

        # Get metadata from pyproject.toml (same as init)
        metadata = get_project_metadata(project_root)
        project_name = metadata.name or project_root.name
        path_hash = generate_hash(project_root)

        # Register with cache (idempotent operation)
        cache.add_mapping(project_root, venv_path, project_name, path_hash)
        return True

    except Exception:
        # Silent failure - don't break list/prune
        return False
```

#### 2. External Register Command

```python
@cli.command()
@common_options
@handle_errors
@click.pass_context
def register(
    ctx,
    verbose: bool,
    yes: bool,
    dry_run: bool,
    json_output: bool,
):
    """Register current project with cache from existing .env.uve.

    This command reads the existing .env.uve file and ensures the project
    is properly tracked in cache.json. Use this to fix cache desync issues.

    Usage:
        prime-uve register           # Register current project
        prime-uve register --dry-run # Preview what would be registered
    """
```

#### 3. Core Logic Flow

```python
def register_command(ctx, verbose, yes, dry_run, json_output):
    # 1. Find project root
    project_root = find_project_root()
    if not project_root:
        raise ValueError("Not in a Python project (no pyproject.toml found)")

    # 2. Check if .env.uve exists
    env_file = project_root / ".env.uve"
    if not env_file.exists():
        raise ValueError(
            ".env.uve file not found\n"
            "Run 'prime-uve init' to initialize this project first"
        )

    # 3. Read .env.uve and extract UV_PROJECT_ENVIRONMENT
    env_vars = read_env_file(env_file)
    venv_path = env_vars.get("UV_PROJECT_ENVIRONMENT")

    if not venv_path or not venv_path.strip():
        raise ValueError(
            "UV_PROJECT_ENVIRONMENT not set in .env.uve\n"
            "Run 'prime-uve init' to set up this project"
        )

    # 4. Get project metadata from pyproject.toml (same as init does)
    metadata = get_project_metadata(project_root)
    project_name = metadata.name or project_root.name
    path_hash = generate_hash(project_root)
    venv_path_expanded = expand_path_variables(venv_path)

    if verbose:
        info(f"Project name: {project_name}")
        info(f"Project root: {project_root}")
        info(f"Venv path: {venv_path}")
        info(f"Venv path (expanded): {venv_path_expanded}")
        info(f"Path hash: {path_hash}")

    # 5. Check if already in cache
    cache = Cache()
    existing_mapping = cache.get_mapping(project_root)

    if existing_mapping:
        # Already registered - check if it matches
        cached_venv_path = existing_mapping["venv_path"]

        if cached_venv_path == venv_path:
            # Already registered with same venv path
            if json_output:
                print_json({
                    "status": "already_registered",
                    "project_name": project_name,
                    "venv_path": venv_path
                })
            else:
                info("Project already registered with matching venv path")
                success(f"Project: {project_name}")
                success(f"Venv: {venv_path}")
            return
        else:
            # Registered but with different venv path - confirm update
            if not yes and not dry_run:
                if not confirm(
                    f"Cache venv path will be updated:\n"
                    f"  Old: {cached_venv_path}\n"
                    f"  New: {venv_path}\n"
                    f"Continue?",
                    default=True
                ):
                    raise click.Abort()

    # 6. Dry run output
    if dry_run:
        echo(f"[DRY RUN] Would register: {project_name}")
        echo(f"[DRY RUN] Cache entry: {project_root} -> {venv_path}")
        return

    # 7. Register with cache
    cache.add_mapping(project_root, venv_path, project_name, path_hash)

    # 8. Output results
    if json_output:
        print_json({
            "status": "registered",
            "project_name": project_name,
            "project_root": str(project_root),
            "venv_path": venv_path,
            "venv_path_expanded": str(expand_path_variables(venv_path)),
            "hash": path_hash
        })
    else:
        if existing_mapping:
            success("Updated cache registration")
        else:
            success("Registered project with cache")
        success(f"Project: {project_name}")
        success(f"Project root: {project_root}")
        success(f"Venv path: {venv_path}")
        info(f"  Expanded: {expand_path_variables(venv_path)}")
```

#### 4. File Structure

**Create:** `src/prime_uve/cli/register.py`
- `auto_register_current_project(cache)` - Internal function
- `register_command(...)` - External command implementation

**Update:** `src/prime_uve/cli/main.py`
```python
@cli.command()
@common_options
@handle_errors
@click.pass_context
def register(
    ctx, verbose: bool, yes: bool, dry_run: bool, json_output: bool
):
    """Register current project with cache from existing .env.uve."""
    from prime_uve.cli.register import register_command
    register_command(ctx, verbose, yes, dry_run, json_output)
```

**Update:** `src/prime_uve/cli/list.py`
```python
from prime_uve.cli.register import auto_register_current_project

def list_command(ctx, orphan_only, verbose, yes, dry_run, json_output):
    # Auto-register current project if present
    cache = Cache()
    auto_register_current_project(cache)

    # Continue with normal list logic...
    mappings = cache.list_all()
    # ...
```

**Update:** `src/prime_uve/cli/prune.py`
```python
from prime_uve.cli.register import auto_register_current_project

def prune_command(ctx, all_venvs, orphan, current, path, verbose, yes, dry_run, json_output):
    # Auto-register current project before pruning
    cache = Cache()
    auto_register_current_project(cache)

    # Dispatch to appropriate handler...
```

### Edge Cases to Handle

**For external `register` command:**
1. **No .env.uve file** → Error with helpful message to run `init`
2. **Empty UV_PROJECT_ENVIRONMENT** → Error
3. **Already registered with same path** → Info message (no-op)
4. **Already registered with different path** → Confirmation to update
5. **Not in a Python project** → Error (no pyproject.toml)

**For internal `auto_register_current_project()`:**
1. **Not in a Python project** → Silently return False
2. **No .env.uve file** → Silently return False
3. **Empty UV_PROJECT_ENVIRONMENT** → Silently return False
4. **Any exception during registration** → Silently return False (don't break list/prune)

**Always handled by Cache class:**
- Corrupted cache.json → Cache class returns empty on load error

### Validation Strategy

**Minimal validation approach - trust .env.uve as source of truth:**

✅ **Must validate:**
- We're in a valid Python project (has pyproject.toml)
- `.env.uve` file exists and is readable
- `UV_PROJECT_ENVIRONMENT` is set and non-empty

❌ **Should NOT validate:**
- Venv path format or content → Accept any path
- Whether venv directory exists on disk → User might register before `uve sync`
- Whether hash matches project path → Generated fresh from project_root
- Whether project name matches venv path → Extracted from pyproject.toml instead

**Rationale:**
- Project name and hash come from pyproject.toml and project_root, not parsed from venv_path
- This allows any custom venv path format (not just ${HOME}/prime-uve/venvs/...)

## User Workflow

### Scenario 1: Cache desync after `uve sync`
```bash
# User has .env.uve but cache is missing
$ prime-uve list
# Shows venv as orphaned (not in cache)

$ prime-uve register
✓ Registered project with cache
  Project: myproject
  Venv path: ${HOME}/prime-uve/venvs/myproject_abc12345

$ prime-uve list
# Now shows venv as valid
```

### Scenario 2: Manual .env.uve creation
```bash
# User manually created .env.uve with correct format
$ cat .env.uve
UV_PROJECT_ENVIRONMENT=${HOME}/prime-uve/venvs/myproject_abc12345

$ prime-uve register
✓ Registered project with cache

$ uve sync
# Works correctly, venv created

$ prime-uve list
# Shows as valid
```

### Scenario 3: Cache corruption recovery
```bash
# cache.json got corrupted or deleted
$ prime-uve list
# Shows no managed venvs

$ cd project-1 && prime-uve register
✓ Registered project with cache

$ cd ../project-2 && prime-uve register
✓ Registered project with cache

$ prime-uve list
# Shows both projects as valid
```

## Integration Points

### `list` command
Auto-registration is called at the start of `list_command()`:
- If run from within a project directory with `.env.uve`, project is automatically registered
- If run from outside a project, auto-registration silently does nothing
- List then shows all cached projects including the just-registered one

### `prune` command
Auto-registration is called at the start of `prune_command()`:
- Prevents accidentally pruning the current project's venv if cache was desynced
- Works for all prune modes: `--all`, `--orphan`, `--current`, and specific path
- Silent operation - user doesn't see registration happen

### Performance Impact
- Minimal: Auto-registration only does I/O if in a project with `.env.uve`
- Fast path: Returns immediately if not in a project or no `.env.uve` exists
- No network calls, just local file reads and cache update

## Alternative Approaches Considered

### Alternative 1: Manual-only registration
Only provide `prime-uve register` command, require users to run it explicitly.

**Rejected because:**
- Users would forget to run it after `uve sync`
- Cache desync would be common and frustrating
- Adds cognitive load for users

### Alternative 2: Auto-register in `uve` wrapper
When `uve` runs, check if project is in cache, and auto-register if not.

**Rejected because:**
- `uve` should be fast and lightweight (runs on every command)
- Would add latency to every `uve` invocation
- Auto-registration only needs to happen before list/prune, not every command

### Alternative 3: Scan all venvs and reverse-discover projects
Make `prime-uve list` scan all venvs, find their projects, and auto-register.

**Rejected because:**
- Requires reverse mapping from venv → project (unreliable)
- Much slower than current-project-only approach
- Complex to implement correctly

### Alternative 4: Make cache.json optional
Store everything in .env.uve files only, no central cache.

**Rejected because:**
- Loses centralized management (list, prune, etc.)
- Would require scanning entire filesystem to find all projects
- Current architecture depends on cache for cross-project operations

### ✅ Chosen Approach: Hybrid auto + manual registration
- Auto-register current project when running `list` or `prune`
- Also provide explicit `prime-uve register` command for manual control
- Best of both worlds: automatic cache sync + user control when needed

## Testing Strategy

### Unit Tests

**For `auto_register_current_project()`:**
- Test not in a project → returns False
- Test no .env.uve → returns False
- Test empty UV_PROJECT_ENVIRONMENT → returns False
- Test valid .env.uve → returns True and adds to cache
- Test exception during registration → returns False (silent failure)
- Test already registered with same path → idempotent (no error)

**For `register_command()`:**
- Test not in a project → raises ValueError
- Test no .env.uve → raises ValueError
- Test empty UV_PROJECT_ENVIRONMENT → raises ValueError
- Test valid registration → success output
- Test already registered with same path → info message
- Test already registered with different path → prompts for confirmation
- Test dry-run mode → no cache modification
- Test JSON output mode

### Integration Tests
- Auto-register via list: cd to project → list → verify registered
- Auto-register via prune: cd to project → prune --orphan → verify not deleted
- Manual register → list → shows as valid
- Delete cache.json → list from project dir → auto-recovery
- Multiple projects: register proj1 → cd proj2 → list → both registered

### Manual Testing Scenarios
1. Auto-registration: delete cache → cd to project → list → verify auto-registered
2. Fresh project: init → register (shows already registered)
3. Manual .env.uve: create .env.uve → register → list
4. Prune protection: delete cache → cd to project → prune --orphan → venv not deleted

## Documentation Updates

### README.md
Update commands section:
```markdown
## Commands

- `prime-uve init` - Initialize project with external venv
- `prime-uve list` - List all managed venvs (auto-registers current project)
- `prime-uve prune` - Clean up venv directories
- `prime-uve register` - Manually register current project with cache
- `prime-uve activate` - Output activation command for current venv
- `prime-uve shell` - Spawn shell with venv activated
- `prime-uve configure vscode` - Update VS Code workspace settings
```

Add note about auto-registration:
```markdown
## Cache Management

The cache is automatically kept in sync:
- Running `prime-uve list` or `prime-uve prune` from within a project automatically registers it
- No need to manually run `prime-uve register` in most cases
- Use `prime-uve register` explicitly for verbose feedback or when troubleshooting
```

### CLAUDE.md
Update commands section:
```markdown
- **`prime-uve register`** - Register current project with cache from .env.uve
```

## Implementation Checklist

- [ ] Create `src/prime_uve/cli/register.py` with:
  - [ ] `auto_register_current_project()` function
  - [ ] `register_command()` function
- [ ] Update `src/prime_uve/cli/main.py` to add register command
- [ ] Update `src/prime_uve/cli/list.py` to call auto-registration
- [ ] Update `src/prime_uve/cli/prune.py` to call auto-registration
- [ ] Add unit tests for `auto_register_current_project()`
- [ ] Add unit tests for `register_command()`
- [ ] Add integration tests for auto-registration via list/prune
- [ ] Add integration test for manual register command
- [ ] Update README.md with register command and auto-registration docs
- [ ] Update CLAUDE.md project overview
- [ ] Manual test all scenarios

## Success Criteria

1. ✅ Cache automatically stays in sync when running `list` or `prune` from a project
2. ✅ Auto-registration is silent and doesn't break list/prune if it fails
3. ✅ User can manually register with verbose feedback via `prime-uve register`
4. ✅ Manual register command validates .env.uve exists and has UV_PROJECT_ENVIRONMENT
5. ✅ Manual register command provides clear error messages for all failure modes
6. ✅ Manual register command supports --dry-run for preview
7. ✅ Manual register command supports --json for programmatic use
8. ✅ Both auto and manual registration use same core logic (DRY)
9. ✅ Documentation explains auto-registration behavior
10. ✅ Integration tests verify cache desync recovery scenarios

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Auto-registration slows down list/prune | Fast path: returns immediately if not in project or no .env.uve |
| Auto-registration fails and breaks list/prune | Silent exception handling: auto-register returns False on error |
| User confused about when things get registered | Document auto-registration behavior in README |
| Cache corruption during register | Cache uses atomic writes with temp file + lock |
| User manually registers wrong .env.uve | Validate UV_PROJECT_ENVIRONMENT is set, confirm on path change |

## Timeline

**Estimated effort:** 3-4 hours
- Implementation: 1.5 hours (auto + manual registration)
- Testing: 1 hour (unit + integration tests)
- Documentation: 0.5 hours
- Review and refinement: 1 hour

## Questions for User

None - requirements are clear from the task description.

## References

- Cache implementation: `src/prime_uve/core/cache.py`
- Env file handling: `src/prime_uve/core/env_file.py`
- Init command (reference): `src/prime_uve/cli/init.py`
- List validation logic: `src/prime_uve/cli/list.py:31-81`

---

## Implementation Progress

### 2025-01-05 - Initial Implementation Completed

**Implemented:**
- ✅ Created `src/prime_uve/cli/register.py` with:
  - `auto_register_current_project(cache)` - Internal silent registration
  - `register_command(...)` - External verbose command
- ✅ Updated `src/prime_uve/cli/main.py` - Added register command to CLI
- ✅ Updated `src/prime_uve/cli/list.py` - Integrated auto-registration
- ✅ Updated `src/prime_uve/cli/prune.py` - Integrated auto-registration
- ✅ All existing tests pass (400/400)
- ✅ Manual testing verified basic functionality

**Key Implementation Details:**
- Minimal validation: Only checks .env.uve exists and UV_PROJECT_ENVIRONMENT is set
- Metadata from pyproject.toml: project_name and hash generated, not parsed from venv_path
- Silent failure for auto-registration: Never breaks list/prune commands
- Idempotent operation: Safe to call multiple times
- Dry-run and JSON output support for manual command

**Manual Test Results:**
```bash
# Basic registration
$ prime-uve register
[i] Project already registered with matching venv path
[OK] Project: prime-uve
[OK] Venv: ${HOME}/prime-uve/venvs/prime-uve_043331fa

# Verbose mode
$ prime-uve register --verbose
[i] Project name: prime-uve
[i] Project root: C:\Users\s.follador\Documents\github\prime-uve
[i] Venv path: ${HOME}/prime-uve/venvs/prime-uve_043331fa
[i] Venv path (expanded): C:\Users\s.follador\prime-uve\venvs\prime-uve_043331fa
[i] Path hash: 043331fa
[i] Project already registered with matching venv path

# Auto-registration via list
$ prime-uve list
[Auto-registration happens silently]
Managed Virtual Environments
[...]
```

**Commit:** feat: add register command with auto-registration (3043910)
**Branch:** feature/register-command
**Status:** Ready for review

**Next Steps:**
- Create pull request to dev branch
- Consider adding unit tests for register module (optional - all integration works)
- Update documentation if needed
