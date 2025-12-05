# Proposal: VS Code Configuration Improvements

## Original Objective

VS Code's `configure vscode` command doesn't fully configure VS Code for proper venv integration. Issues:
1. VS Code shows warning about default interpreter path being incorrect
2. VS Code doesn't spawn new terminals with the virtual environment activated
3. Poor discoverability - users don't know what settings are needed

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

### What's Missing

VS Code needs additional settings for full venv integration:

1. **`python.terminal.activateEnvironment`**: Should be `true` to auto-activate venv in terminals
2. **`python.envFile`**: Should point to `.env.uve` so VS Code loads environment variables
3. **Variable expansion**: VS Code may not expand `${HOME}` correctly on all platforms
4. **Settings location**: Workspace settings vs folder settings (`.vscode/settings.json`)

### The Core Problem

VS Code has two configuration systems:
- **Workspace files** (`.code-workspace`): Multi-folder workspaces
- **Folder settings** (`.vscode/settings.json`): Single-folder projects

Current implementation only handles workspace files. Most users use folder settings.

## Proposed Solution

### 1. Support Both Configuration Methods

Detect and configure both:

**Priority order**:
1. If `.code-workspace` exists → update workspace file
2. Else → create/update `.vscode/settings.json`

### 2. Complete Settings Configuration

Apply all necessary settings:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.terminal.activateEnvironment": true,
  "python.envFile": "${workspaceFolder}/.env.uve"
}
```

**Note**: Use `${workspaceFolder}` for relative paths when possible.

### 3. Path Resolution Strategy

VS Code has mixed support for environment variables:

**Problem**: `${HOME}` doesn't always work in VS Code settings.

**Solution**: Use a hybrid approach:
- **Workspace file**: Use `${HOME}` for cross-user compatibility
- **Folder settings**: Use expanded absolute path (user-specific)

Rationale:
- Workspace files are often committed to git → need portability
- Folder settings (`.vscode/`) are often gitignored → can be user-specific

### 4. Improved User Guidance

After configuration, show actionable next steps:

```
✓ VS Code configured successfully

Settings applied:
  - Python interpreter: <path>
  - Terminal auto-activation: enabled
  - Environment file: .env.uve

Next steps:
  1. Reload VS Code window (Ctrl+Shift+P → "Developer: Reload Window")
  2. Open a new terminal (Ctrl+`) to verify venv activation
  3. If issues persist, select interpreter manually:
     Ctrl+Shift+P → "Python: Select Interpreter"
```

### 5. Validation and Troubleshooting

Add `--verify` flag to check if configuration is working:

```bash
prime-uve configure vscode --verify
```

This would:
1. Check if settings files exist
2. Verify interpreter path exists
3. Check if `.env.uve` exists
4. Report any issues with fix suggestions

## Implementation Plan

### Phase 1: Folder Settings Support

1. **File**: `src/prime_uve/utils/vscode.py`
   - Add `read_folder_settings()` function
   - Add `write_folder_settings()` function
   - Add `update_folder_settings()` function (like workspace but for `.vscode/settings.json`)

2. **File**: `src/prime_uve/cli/configure.py`
   - Update `configure_vscode_command()` logic
   - Priority: workspace file → folder settings
   - Default to folder settings if neither exists

3. **Tests**: `tests/test_cli/test_configure.py`
   - Test folder settings creation
   - Test folder settings update
   - Test priority order (workspace takes precedence)

### Phase 2: Complete Settings Set

1. **File**: `src/prime_uve/utils/vscode.py`
   - Update settings application to include:
     - `python.terminal.activateEnvironment`: `true`
     - `python.envFile`: `"${workspaceFolder}/.env.uve"` (or absolute)

2. **File**: `src/prime_uve/cli/configure.py`
   - Apply complete settings set in both workspace and folder modes

3. **Tests**: `tests/test_cli/test_configure.py`
   - Verify all settings are applied
   - Test that existing settings are preserved

### Phase 3: Path Resolution Strategy

1. **File**: `src/prime_uve/utils/vscode.py`
   - For **workspace files**: Use `${HOME}` in path
   - For **folder settings**: Use expanded absolute path
   - Document rationale in code comments

2. **File**: `src/prime_uve/cli/configure.py`
   - Implement hybrid path strategy
   - Add `--use-absolute-paths` flag to force absolute paths everywhere

3. **Tests**: `tests/test_cli/test_configure.py`
   - Test workspace gets `${HOME}` path
   - Test folder settings get absolute path
   - Test `--use-absolute-paths` flag

### Phase 4: Improved User Guidance

1. **File**: `src/prime_uve/cli/configure.py`
   - Enhance success message with next steps
   - List all applied settings
   - Add troubleshooting hints

2. **File**: `src/prime_uve/cli/output.py` (if needed)
   - Add helper for formatted instruction lists

### Phase 5: Verification Mode

1. **File**: `src/prime_uve/cli/configure.py`
   - Add `--verify` flag
   - Implement verification checks:
     - Settings files exist
     - Interpreter path exists on disk
     - `.env.uve` exists
     - Settings values match expected

2. **Tests**: `tests/test_cli/test_configure.py`
   - Test `--verify` with correct setup
   - Test `--verify` with missing files
   - Test `--verify` with mismatched settings

## Example Outputs

### Current (Workspace File)
```bash
$ prime-uve configure vscode
✓ VS Code configured successfully
Updated workspace: prime-uve.code-workspace
```

### Proposed (Folder Settings)
```bash
$ prime-uve configure vscode
✓ VS Code configured successfully

Configuration:
  Location:    .vscode/settings.json
  Interpreter: C:\Users\user\.prime-uve\venvs\prime-uve_hash\Scripts\python.exe

Settings applied:
  ✓ python.defaultInterpreterPath
  ✓ python.terminal.activateEnvironment
  ✓ python.envFile

Next steps:
  1. Reload VS Code window:
     Ctrl+Shift+P → "Developer: Reload Window"

  2. Open new terminal (Ctrl+`) to verify venv activation
     You should see: (prime-uve) in the terminal prompt

  3. If interpreter not detected:
     Ctrl+Shift+P → "Python: Select Interpreter"
     → Choose: C:\Users\user\.prime-uve\venvs\prime-uve_hash\Scripts\python.exe

  4. Check output panel for errors:
     Ctrl+Shift+U → Select "Python" from dropdown
```

### Verification Mode
```bash
$ prime-uve configure vscode --verify
Verifying VS Code configuration...

✓ Settings file exists: .vscode/settings.json
✓ Interpreter path valid: C:\Users\user\.prime-uve\venvs\prime-uve_hash\Scripts\python.exe
✓ Environment file exists: .env.uve
✓ python.defaultInterpreterPath: Set correctly
✓ python.terminal.activateEnvironment: Enabled
✓ python.envFile: Set correctly

All checks passed! VS Code should be configured correctly.

If terminals still don't activate venv:
  - Try reloading VS Code window
  - Check for conflicting settings in User settings
  - Verify .env.uve contains UV_PROJECT_ENVIRONMENT
```

## Edge Cases

1. **Both workspace and folder settings exist**: Prefer workspace file (explicitly inform user)
2. **`.vscode/` directory doesn't exist**: Create it
3. **`.vscode/settings.json` has comments**: Preserve them if possible (use `strip_json_comments` or warn user)
4. **Conflicting user-level settings**: Detect and warn (verification mode)
5. **Multiple workspace files**: Already handled by existing code (prompts user)
6. **Interpreter doesn't exist yet**: Warn but still configure (user might create venv later)

## Alternative Approaches

### Option A: Generate VS Code Tasks
Instead of just settings, generate tasks for common operations:
```json
{
  "tasks": [
    {
      "label": "Activate venv",
      "type": "shell",
      "command": "prime-uve activate"
    }
  ]
}
```

**Decision**: Out of scope for this task. Consider as future enhancement.

### Option B: VS Code Extension
Create a VS Code extension that integrates prime-uve directly.

**Decision**: Too large for current scope. Current solution should work without extension.

### Option C: Symlink `.venv` in Project Root
Create `.venv` symlink pointing to external venv. VS Code auto-detects `.venv/`.

**Pros**:
- Zero configuration needed
- Works with all tools, not just VS Code

**Cons**:
- Symlinks unreliable on Windows (requires admin or developer mode)
- Clashes with uv's `.venv` if user runs `uv venv`
- Adds complexity to prime-uve's mental model

**Decision**: Consider as separate feature. Don't mix with configure command.

## Breaking Changes

None. Existing workspace file configuration continues to work.

## Dependencies

No new dependencies.

## Testing Strategy

1. **Unit tests**: Settings file manipulation functions
2. **Integration tests**: Full configure workflow
3. **Manual testing**:
   - Test on Windows with folder settings
   - Test on macOS with workspace file
   - Verify terminal activation works
   - Test verification mode

## Success Criteria

After running `prime-uve configure vscode`:
1. ✓ VS Code detects correct Python interpreter
2. ✓ New terminals auto-activate venv (shows `(project-name)` in prompt)
3. ✓ No warnings in VS Code Python extension
4. ✓ User understands what was configured and how to troubleshoot

## Questions for User

1. **Default configuration**: Should we default to folder settings (`.vscode/settings.json`) or workspace file (`.code-workspace`)? Current implementation prefers workspace files.

2. **Path strategy**: Confirm the hybrid approach (workspace uses `${HOME}`, folder uses absolute). Or always use absolute?

3. **Terminal activation**: Should we also configure the shell integration settings (`python.terminal.activateEnvInCurrentTerminal`)?

4. **Verification flag**: Include in first release or add later?

5. **Multi-root workspaces**: How should we handle VS Code multi-root workspaces? Current implementation handles them, but should we detect and apply settings to all folders?
