# Proposal: prime-uve list Improvements

## Original Objective

Improve the `prime-uve list` command table output for better usability:
1. Move status to first column and display only `[OK]`/`[!]` for compact width
2. Show project path to allow quick navigation (prefer clickable links if possible)
3. Highlight current project when `prime-uve list` is run from a managed project
4. Add `--no-auto-register` option to prevent automatic registration

## Analysis

### Current Behavior
- **Table format**: `PROJECT | STATUS | VENV PATH`
- **Status column**: Shows `[OK] Valid` or `[!] Orphan` (15 chars wide)
- **Auto-registration**: Both `list` and `prune` silently call `auto_register_current_project()` before execution
- **Project path**: Only shown in verbose mode (`-v`), not in standard table

### Problems to Solve
1. **Verbose status**: `[OK] Valid` and `[!] Orphan` waste horizontal space
2. **Missing project path**: Users can't easily navigate to projects without `-v`
3. **No current project indicator**: User doesn't know which row is their current project
4. **Unwanted auto-registration**: Users running `list` or `prune` to inspect state may not want silent cache updates

## Proposed Solution

### 1. Table Column Redesign

**New format**: `STATUS | PROJECT | PROJECT PATH | VENV PATH`

**Status column** (3 chars):
- `[OK]` for valid projects (green)
- `[!]` for orphans (red)
- Remove "Valid"/"Orphan" text labels

**Project column** (20 chars):
- Show project name
- Append `(current)` suffix if this is the current project
- Color: dim/gray for normal, bright/bold for current

**Project path column** (variable):
- Show absolute project path
- Make it terminal-clickable (many modern terminals support Ctrl+Click on paths)
- Truncate intelligently if needed (keep end of path visible)

**Venv path column** (variable):
- Show expanded venv path (as before)
- Keep full path for terminal clickability

### 2. Current Project Detection

Add helper function to detect if user is currently in a project:
```python
def get_current_project_root() -> Path | None:
    """Get current project root if in a managed project."""
    try:
        return find_project_root()
    except Exception:
        return None
```

When rendering table, check if `result.project_path == current_project_root` and:
- Add `(current)` suffix to project name
- Use bold/bright formatting for the row

### 3. Auto-Registration Control

Add `--no-auto-register` flag to both `list` and `prune` commands:

```python
@click.command()
@click.option('--no-auto-register', is_flag=True,
              help='Skip automatic registration of current project')
@common_options
def list_command(no_auto_register: bool, ...):
    cache = Cache()

    # Only auto-register if flag not set
    if not no_auto_register:
        registered = auto_register_current_project(cache)
        # More on this below...

    # ... rest of command
```

### 4. Registration Notification

**Current problem**: `auto_register_current_project()` is silent. Users running `prime-uve list` after deleting cache will see the project re-appear without knowing why.

**Solution**: Make the function return registration status and display a message:

```python
# In register.py
def auto_register_current_project(cache: Cache) -> tuple[bool, str | None]:
    """Auto-register current project.

    Returns:
        (was_registered, project_name) or (False, None)
    """
    # ... existing logic ...
    if registration_happened:
        return (True, project_name)
    return (False, None)

# In list.py
if not no_auto_register:
    was_registered, project_name = auto_register_current_project(cache)
    if was_registered:
        info(f"Registered current project '{project_name}' in cache")
```

This solves the confusion problem described in the "register message" task.

## Implementation Plan

### Phase 1: Table Redesign (Core)
1. **File**: `src/prime_uve/cli/list.py`
   - Update `output_table()` function
   - Change header format to: `STATUS | PROJECT | PROJECT PATH | VENV PATH`
   - Reduce status display to just `[OK]` or `[!]`
   - Add project_path column
   - Adjust column widths

2. **Test updates**: `tests/test_cli/test_list.py`
   - Update assertions for new table format
   - Add tests for column widths
   - Verify project path appears in standard (non-verbose) mode

### Phase 2: Current Project Highlighting
1. **File**: `src/prime_uve/cli/list.py`
   - Add `get_current_project_root()` helper
   - In `output_table()`, detect current project
   - Add `(current)` suffix to project name
   - Apply bold/bright formatting to current row

2. **Test updates**: `tests/test_cli/test_list.py`
   - Test current project detection
   - Test `(current)` suffix appears
   - Test when not in any project (no highlighting)

### Phase 3: Auto-Registration Control
1. **Files**:
   - `src/prime_uve/cli/list.py` - add `--no-auto-register` flag
   - `src/prime_uve/cli/prune.py` - add `--no-auto-register` flag

2. **Test updates**:
   - `tests/test_cli/test_list.py` - test `--no-auto-register` prevents registration
   - `tests/test_cli/test_prune.py` - test `--no-auto-register` prevents registration

### Phase 4: Registration Notification
1. **File**: `src/prime_uve/cli/register.py`
   - Change `auto_register_current_project()` return type
   - Return `(was_registered: bool, project_name: str | None)`
   - Update docstring

2. **Files**: `src/prime_uve/cli/list.py`, `src/prime_uve/cli/prune.py`
   - Update calls to `auto_register_current_project()`
   - Display info message when registration occurs
   - Message: `"Registered current project '{project_name}' in cache"`

3. **Test updates**:
   - Test registration message appears
   - Test message doesn't appear when already registered
   - Test message doesn't appear with `--no-auto-register`

## Example Output

### Before (Current)
```
Managed Virtual Environments

PROJECT              STATUS          VENV PATH
--------------------------------------------------------------------------------
prime-uve            [OK] Valid      C:\Users\user\.prime-uve\venvs\prime-uve_043331fa
test-project         [!] Orphan      C:\Users\user\.prime-uve\venvs\test-project_abc123

Summary: 2 total, 1 valid, 1 orphaned
```

### After (Proposed)
```
Managed Virtual Environments

[OK] Registered current project 'prime-uve' in cache

STATUS | PROJECT             | PROJECT PATH                                  | VENV PATH
-------------------------------------------------------------------------------------------
[OK]   | prime-uve (current) | C:\Users\user\Documents\github\prime-uve      | C:\Users\user\.prime-uve\venvs\prime-uve_043331fa
[!]    | test-project        | C:\Users\user\Projects\test-project           | C:\Users\user\.prime-uve\venvs\test-project_abc123

Summary: 2 total, 1 valid, 1 orphaned
```

**Note**: The `(current)` row would be bold/bright in actual terminal output.

## Terminal Link Clickability

Modern terminals (Windows Terminal, iTerm2, VSCode integrated terminal, etc.) auto-detect file paths and make them clickable. No special formatting needed - just output the full absolute path.

**Alternative approach**: Use OSC 8 hyperlinks for explicit clickable links:
```python
# Format: \033]8;;file://path\033\\text\033]8;;\033\\
def make_hyperlink(path: Path, text: str) -> str:
    return f"\033]8;;file://{path}\033\\{text}\033]8;;\033\\"
```

This would allow showing shortened text while maintaining clickability, but adds complexity. **Recommendation**: Start with plain paths and add hyperlinks later if needed.

## Edge Cases

1. **Very long project paths**: Truncate intelligently (keep rightmost part)
2. **Project path doesn't exist**: Show path with warning indicator
3. **Multiple projects in same directory**: Hash differentiates them
4. **Running list from outside any project**: No `(current)` highlighting
5. **Terminal too narrow**: Columns may wrap - acceptable trade-off

## Breaking Changes

None. This is purely additive/cosmetic. The `--no-auto-register` flag is optional.

## Dependencies

No new dependencies needed.

## Testing Strategy

1. **Unit tests**: Test individual functions (current project detection, formatting)
2. **CLI tests**: Test flag behavior and output format
3. **Integration tests**: Test with real projects and paths
4. **Manual testing**: Verify terminal clickability on Windows Terminal, iTerm2, VSCode

## Timeline

- Phase 1 (Table redesign): 1-2 hours
- Phase 2 (Current highlighting): 1 hour
- Phase 3 (Auto-register flag): 1 hour
- Phase 4 (Registration message): 1 hour
- Testing: 1-2 hours

**Total estimate**: 5-7 hours

## Questions for User

1. **Column order preference**: Is `STATUS | PROJECT | PROJECT PATH | VENV PATH` the right order? Or prefer `PROJECT | STATUS | PROJECT PATH | VENV PATH`?

2. **Project path display**: Full absolute path, or relative to home (`~/Documents/...`)?

3. **Registration message**: Should it be `info()` (blue), `success()` (green), or just plain `echo()`?

4. **Current project indicator**: Prefer `(current)` suffix or a different marker like `*` or `→`?

5. **Table separator**: Keep the `------` line or remove for cleaner look?
