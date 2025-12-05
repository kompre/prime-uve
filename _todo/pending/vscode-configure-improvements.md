# Proposal: VS Code Workspace Configuration Improvements

## Original Objective

VS Code's `configure vscode` command doesn't fully configure VS Code for proper venv integration. Issues:
1. VS Code doesn't spawn new terminals with the virtual environment activated
2. VS Code doesn't load environment variables from `.env.uve`
3. Poor user guidance - users don't know what was configured or how to troubleshoot

## Problem Analysis

### Current Implementation

The `configure vscode` command updates the workspace file (`.code-workspace`) with:
```json
{
  "settings": {
    "python.defaultInterpreterPath": "${HOME}/.prime-uve/venvs/project_hash/Scripts/python.exe"
  }
}
```

**What works**:
- Sets Python interpreter correctly
- Uses `${HOME}` for cross-platform compatibility
- Handles workspace discovery and creation

### What's Missing

VS Code needs additional workspace settings for complete venv integration:

1. **`python.terminal.activateEnvironment`**: Must be `true` to auto-activate venv in new terminals
2. **`python.envFile`**: Should point to `.env.uve` so VS Code loads `UV_PROJECT_ENVIRONMENT`

Without these settings:
- New terminals don't show `(project-name)` prompt
- Environment variables from `.env.uve` aren't loaded
- Users manually activate venv each time

### Scope Decision

**ONLY support `.code-workspace` files.**

Rationale:
- Workspace files are prime-uve's existing pattern
- Simpler implementation and testing
- Clear mental model: one workspace file per project
- Users who prefer folder settings can manually copy settings from workspace file
- Avoids complexity of supporting two configuration systems

## Proposed Solution

### 1. Complete Settings Set

Apply all necessary settings to workspace file:

```json
{
  "folders": [{"path": "."}],
  "settings": {
    "python.defaultInterpreterPath": "${HOME}/.prime-uve/venvs/project_hash/Scripts/python.exe",
    "python.terminal.activateEnvironment": true,
    "python.envFile": "${workspaceFolder}/.env.uve"
  }
}
```

**Changes from current**:
- Add `python.terminal.activateEnvironment: true` - enables auto-activation in new terminals
- Add `python.envFile: "${workspaceFolder}/.env.uve"` - loads UV_PROJECT_ENVIRONMENT variable

**Path strategy**:
- `python.defaultInterpreterPath`: Use `${HOME}` (current behavior, cross-platform)
- `python.envFile`: Use `${workspaceFolder}` (workspace-relative, always correct)

### 2. Improved User Guidance

After configuration, show what was done and next steps:

```
✓ VS Code workspace configured

Workspace: prime-uve.code-workspace

Settings applied:
  ✓ Python interpreter: ${HOME}/.prime-uve/venvs/prime-uve_hash/Scripts/python.exe
  ✓ Terminal auto-activation: enabled
  ✓ Environment file: .env.uve

Next steps:
  1. Open workspace in VS Code:
     code prime-uve.code-workspace

  2. Reload window if already open:
     Ctrl+Shift+P → "Developer: Reload Window"

  3. Open new terminal (Ctrl+`):
     Should show: (prime-uve) in prompt

  4. If interpreter not detected:
     Ctrl+Shift+P → "Python: Select Interpreter"
```

**Benefits**:
- Clear visibility into what was configured
- Actionable troubleshooting steps
- User knows exactly what to expect

### 3. Verification Mode (Optional Future Enhancement)

Add `--verify` flag to validate configuration:

```bash
prime-uve configure vscode --verify
```

Would check:
1. Workspace file exists and is valid JSON
2. Interpreter path exists on disk
3. `.env.uve` exists
4. All three settings are present and correct

**Decision**: Defer to future release. Current scope is adding complete settings.

## Implementation Plan

### Phase 1: Add Complete Settings to Workspace

1. **File**: `src/prime_uve/utils/vscode.py`
   - Update `update_python_interpreter()` to `update_workspace_settings()`
   - Add all three settings:
     - `python.defaultInterpreterPath` (existing)
     - `python.terminal.activateEnvironment: true` (new)
     - `python.envFile: "${workspaceFolder}/.env.uve"` (new)
   - Update `create_default_workspace()` to include all settings

2. **File**: `src/prime_uve/cli/configure.py`
   - Update function call from `update_python_interpreter()` to `update_workspace_settings()`
   - No other logic changes needed

3. **Tests**: `tests/test_utils/test_vscode.py`
   - Update existing tests for renamed function
   - Verify all three settings are applied
   - Test that existing settings are preserved (merged, not replaced)

### Phase 2: Enhanced User Guidance

1. **File**: `src/prime_uve/cli/configure.py`
   - Replace current success messages with detailed output:
     - Show workspace filename
     - List all three settings applied
     - Show 4-step next steps guide
   - Use existing output functions (success, info, echo)

2. **Tests**: `tests/test_cli/test_configure.py`
   - Update snapshot tests for new output format
   - Verify all guidance text appears in output

## Example Outputs

### Current
```bash
$ prime-uve configure vscode
✓ Updated prime-uve.code-workspace
✓ Python interpreter set to venv

VS Code will detect the change automatically if open.
If not, restart VS Code or reload the window.
```

### Proposed
```bash
$ prime-uve configure vscode
✓ VS Code workspace configured

Workspace: prime-uve.code-workspace

Settings applied:
  ✓ Python interpreter: ${HOME}/.prime-uve/venvs/prime-uve_043331fa/Scripts/python.exe
  ✓ Terminal auto-activation: enabled
  ✓ Environment file: .env.uve

Next steps:
  1. Open workspace in VS Code:
     code prime-uve.code-workspace

  2. Reload window if already open:
     Ctrl+Shift+P → "Developer: Reload Window"

  3. Open new terminal (Ctrl+`):
     Should show: (prime-uve) in prompt

  4. If interpreter not detected:
     Ctrl+Shift+P → "Python: Select Interpreter"
```

## Edge Cases

1. **Multiple workspace files**: Already handled - prompts user to choose
2. **Workspace file has existing settings**: Merge new settings, preserve others
3. **Workspace file malformed**: Already handled - offers to backup and regenerate
4. **Interpreter doesn't exist yet**: Already handled - validation checks before configuring
5. **User has conflicting settings in User-level config**: Not our problem - workspace settings override user settings in VS Code

## Breaking Changes

None. Adds two new settings to workspace files without removing or changing existing behavior.

## Dependencies

None. Uses existing VS Code workspace utilities.

## Testing Strategy

1. **Unit tests**: `tests/test_utils/test_vscode.py`
   - Test `update_workspace_settings()` adds all three settings
   - Test `create_default_workspace()` includes all three settings
   - Test merging with existing settings preserves other keys

2. **Integration tests**: `tests/test_cli/test_configure.py`
   - Test complete workflow produces workspace with all settings
   - Test output messages contain expected guidance

3. **Manual testing**:
   - Run on Windows and verify terminal auto-activation
   - Check that `.env.uve` variables are loaded
   - Verify workspace file is valid JSON

## Success Criteria

After running `prime-uve configure vscode`:
1. ✓ Workspace file contains all three Python settings
2. ✓ New terminals auto-activate venv (shows `(project-name)` in prompt)
3. ✓ Environment variables from `.env.uve` are loaded in Python extension
4. ✓ User receives clear guidance on next steps

## Effort Estimate

- Phase 1 (Add settings): 1-2 hours
- Phase 2 (Enhanced guidance): 30 minutes
- Testing: 1 hour

**Total**: 2.5-3.5 hours
