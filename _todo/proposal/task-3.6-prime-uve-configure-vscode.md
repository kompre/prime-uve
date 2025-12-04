# Task 3.6: Implement `prime-uve configure vscode`

## Objective

Implement the `prime-uve configure vscode` command to update VS Code workspace settings with the correct Python interpreter path from the project's venv. This enables IDE features like IntelliSense, debugging, and linting to work correctly with the external venv.

## Context

VS Code needs to know where the Python interpreter is located to provide IDE features. When using external venvs (not in `.venv`), VS Code won't auto-discover them. This command automates updating the workspace settings to point to the correct interpreter.

## Dependencies

**Required (all complete):**
- Task 1.1: Path generation and expansion ✅
- Task 1.3: .env.uve management ✅
- Task 1.4: Project detection ✅
- Task 3.1: CLI framework ✅

**Beneficial:**
- Task 3.2: `prime-uve init` - Creates venvs to configure

## Deliverables

### 1. Implementation Files

**`src/prime_uve/cli/configure.py`** (~250-300 lines)
- Main `configure` command group
- `vscode` subcommand implementation
- Workspace file discovery (.code-workspace)
- JSON parsing and updating (preserve existing settings)
- Multiple workspace file handling
- Create workspace file if needed

**`src/prime_uve/utils/vscode.py`** (~150 lines)
- VS Code workspace utilities:
  - `find_workspace_files(project_root: Path) -> list[Path]` - Find .code-workspace files
  - `read_workspace(path: Path) -> dict` - Parse workspace JSON
  - `write_workspace(path: Path, data: dict)` - Write workspace JSON
  - `update_python_interpreter(workspace: dict, interpreter_path: Path) -> dict` - Update settings
  - `create_default_workspace(project_root: Path, interpreter_path: Path) -> dict` - Generate new workspace

### 2. Test Suite

**`tests/test_cli/test_configure.py`** (~15-18 tests)

**Test Categories:**

1. **Basic Functionality** (5 tests)
   - Updates existing workspace file
   - Creates new workspace file if none exists
   - Sets python.defaultInterpreterPath correctly
   - Preserves other workspace settings
   - Shows success message

2. **Multiple Workspace Files** (3 tests)
   - Multiple .code-workspace files found → prompts user
   - User selects specific file
   - `--workspace` option specifies file

3. **Edge Cases** (4 tests)
   - No .env.uve (error)
   - Venv doesn't exist (error)
   - Malformed workspace JSON (backup and recreate)
   - Empty workspace file (add minimal structure)

4. **Confirmation and Safety** (3 tests)
   - Existing interpreter setting → shows confirmation
   - `--yes` skips confirmation
   - `--dry-run` shows what would change

5. **Options** (3 tests)
   - `--create` creates workspace even if exists
   - `--workspace PATH` specifies workspace file
   - Verbose mode shows details

**`tests/test_utils/test_vscode.py`** (~12 tests)

1. **Workspace Discovery** (4 tests)
   - Find single workspace file
   - Find multiple workspace files
   - No workspace files found
   - Recursive search in subdirectories

2. **JSON Handling** (4 tests)
   - Read valid workspace file
   - Write workspace file
   - Handle malformed JSON
   - Preserve formatting and comments (where possible)

3. **Setting Updates** (4 tests)
   - Add python.defaultInterpreterPath to empty settings
   - Update existing python.defaultInterpreterPath
   - Preserve other Python settings
   - Create default workspace structure

### 3. Integration Points

**CLI Command Registration** (in `main.py`):
```python
from prime_uve.cli import configure

@cli.group()
def configure_group():
    """Configure IDE and tool integration."""
    pass

@configure_group.command(name='vscode')
@click.option('--workspace', type=click.Path(), help='Specific workspace file path')
@click.option('--create', is_flag=True, help='Create new workspace file')
@common_options
@handle_errors
def configure_vscode_cmd(ctx, workspace, create, verbose, yes, dry_run, json_output):
    """Update VS Code workspace with venv path."""
    from prime_uve.cli.configure import configure_vscode_command
    configure_vscode_command(ctx, workspace, create, verbose, yes, dry_run, json_output)
```

## Command Specification

### Usage

```bash
prime-uve configure vscode [OPTIONS]
```

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--workspace PATH` | | auto-discover | Specific workspace file to update |
| `--create` | | False | Create new workspace file |
| `--verbose` | `-v` | False | Show detailed output |
| `--yes` | `-y` | False | Skip confirmation prompts |
| `--dry-run` | | False | Show what would change |
| `--json` | | False | Output as JSON |

### Output Examples

**Success (existing workspace):**
```
Found workspace: myproject.code-workspace

Current interpreter: /usr/bin/python3
New interpreter:     /home/user/prime-uve/venvs/myproject_a1b2c3d4/bin/python

Update workspace? [Y/n]: y

✓ Updated workspace file
✓ Python interpreter set to venv

VS Code will detect the change automatically if open.
If not, restart VS Code or reload the window.
```

**Success (create new workspace):**
```
No workspace file found. Creating new one...

✓ Created myproject.code-workspace
✓ Python interpreter set to venv

To use:
  1. Open workspace: code myproject.code-workspace
  2. VS Code will load with correct interpreter
```

**Success (--dry-run):**
```
[DRY RUN] Would update workspace: myproject.code-workspace

[DRY RUN] Changes:
  settings.python.defaultInterpreterPath:
    Old: /usr/bin/python3
    New: /home/user/prime-uve/venvs/myproject_a1b2c3d4/bin/python
```

**Multiple workspace files found:**
```
Multiple workspace files found:

  [1] myproject.code-workspace
  [2] .vscode/project.code-workspace

Which workspace should be updated? [1-2, 0 to cancel]: 1

✓ Updated myproject.code-workspace
✓ Python interpreter set to venv
```

**Success (--json):**
```json
{
  "workspace_file": "/home/user/projects/myproject/myproject.code-workspace",
  "created": false,
  "updated": true,
  "interpreter_path": "/home/user/prime-uve/venvs/myproject_a1b2c3d4/bin/python",
  "previous_interpreter": "/usr/bin/python3"
}
```

**Error (not initialized):**
```
✗ Error: Project not initialized
  No .env.uve file found.

  Run 'prime-uve init' to initialize the project.
```

**Error (venv doesn't exist):**
```
✗ Error: Venv not found
  Expected venv at: /home/user/prime-uve/venvs/myproject_a1b2c3d4

  To recreate: Run 'prime-uve init --force'
```

## Implementation Logic

### Main Flow

```python
def configure_vscode_command(ctx, workspace_path, create, verbose, yes, dry_run, json_output):
    # 1. Find project root
    project_root = find_project_root()
    if not project_root:
        raise ValueError("Not in a Python project (no pyproject.toml found)")

    # 2. Find .env.uve and extract venv path
    env_file = find_env_file(project_root)
    if not env_file or not env_file.exists():
        raise ValueError(
            "Project not initialized\n"
            "Run 'prime-uve init' to initialize."
        )

    env_vars = read_env_file(env_file)
    venv_path_var = env_vars.get("UV_PROJECT_ENVIRONMENT")
    if not venv_path_var:
        raise ValueError(".env.uve missing UV_PROJECT_ENVIRONMENT")

    venv_path_expanded = expand_path_variables(venv_path_var)

    if not venv_path_expanded.exists():
        raise ValueError(
            f"Venv not found at: {venv_path_expanded}\n"
            f"To recreate: Run 'prime-uve init --force'"
        )

    # 3. Determine interpreter path (platform-specific)
    if sys.platform == "win32":
        interpreter_path = venv_path_expanded / "Scripts" / "python.exe"
    else:
        interpreter_path = venv_path_expanded / "bin" / "python"

    if not interpreter_path.exists():
        raise ValueError(
            f"Python interpreter not found: {interpreter_path}\n"
            f"Venv may be corrupted. Run 'prime-uve init --force'"
        )

    # 4. Find or create workspace file
    if workspace_path:
        workspace_file = Path(workspace_path)
        if not workspace_file.exists() and not create:
            raise ValueError(f"Workspace file not found: {workspace_file}")
    else:
        workspace_files = find_workspace_files(project_root)

        if not workspace_files:
            if not create and not confirm(
                "No workspace file found. Create one?",
                default=True,
                yes_flag=yes
            ):
                raise click.Abort()

            # Create new workspace
            workspace_file = project_root / f"{project_root.name}.code-workspace"
            workspace_data = create_default_workspace(project_root, interpreter_path)

            if not dry_run:
                write_workspace(workspace_file, workspace_data)
                success(f"Created {workspace_file.name}")
                success("Python interpreter set to venv")
                echo("\nTo use:")
                echo(f"  1. Open workspace: code {workspace_file.name}")
                echo("  2. VS Code will load with correct interpreter")
            else:
                echo(f"[DRY RUN] Would create: {workspace_file}")
                echo(f"[DRY RUN] Interpreter: {interpreter_path}")

            return

        elif len(workspace_files) > 1:
            # Multiple files - prompt user
            echo("Multiple workspace files found:\n")
            for i, wf in enumerate(workspace_files, 1):
                echo(f"  [{i}] {wf.relative_to(project_root)}")

            choice = prompt_choice(
                "\nWhich workspace should be updated?",
                len(workspace_files)
            )

            if choice == 0:
                raise click.Abort()

            workspace_file = workspace_files[choice - 1]
        else:
            workspace_file = workspace_files[0]

    # 5. Update workspace file
    if verbose:
        info(f"Workspace: {workspace_file}")
        info(f"Interpreter: {interpreter_path}")

    workspace_data = read_workspace(workspace_file)

    # Check if interpreter already set
    current_interpreter = workspace_data.get("settings", {}).get("python.defaultInterpreterPath")

    if current_interpreter and current_interpreter != str(interpreter_path) and not yes:
        echo(f"\nCurrent interpreter: {current_interpreter}")
        echo(f"New interpreter:     {interpreter_path}")
        if not confirm("\nUpdate workspace?", default=True, yes_flag=yes):
            raise click.Abort()

    # Update settings
    workspace_data = update_python_interpreter(workspace_data, interpreter_path)

    # Write changes
    if dry_run:
        echo(f"[DRY RUN] Would update workspace: {workspace_file.name}")
        echo("\n[DRY RUN] Changes:")
        echo(f"  settings.python.defaultInterpreterPath:")
        echo(f"    Old: {current_interpreter or '(not set)'}")
        echo(f"    New: {interpreter_path}")
    else:
        write_workspace(workspace_file, workspace_data)
        success(f"Updated {workspace_file.name}")
        success("Python interpreter set to venv")
        echo("\nVS Code will detect the change automatically if open.")
        echo("If not, restart VS Code or reload the window.")

    if json_output:
        output_json({
            "workspace_file": str(workspace_file),
            "created": False,
            "updated": True,
            "interpreter_path": str(interpreter_path),
            "previous_interpreter": current_interpreter
        })
```

### Workspace File Operations

```python
def find_workspace_files(project_root: Path) -> list[Path]:
    """Find all .code-workspace files in project."""
    workspace_files = []

    # Check project root
    for file in project_root.glob("*.code-workspace"):
        workspace_files.append(file)

    # Check .vscode directory
    vscode_dir = project_root / ".vscode"
    if vscode_dir.exists():
        for file in vscode_dir.glob("*.code-workspace"):
            workspace_files.append(file)

    return sorted(workspace_files)

def read_workspace(path: Path) -> dict:
    """Read and parse workspace JSON file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            # JSON with comments is technically invalid, but VS Code allows it
            # Strip comments before parsing
            content = f.read()
            content = strip_json_comments(content)
            return json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed workspace file: {e}")

def write_workspace(path: Path, data: dict):
    """Write workspace JSON file with proper formatting."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')  # Trailing newline

def update_python_interpreter(workspace: dict, interpreter_path: Path) -> dict:
    """Update Python interpreter setting in workspace data."""
    if "settings" not in workspace:
        workspace["settings"] = {}

    workspace["settings"]["python.defaultInterpreterPath"] = str(interpreter_path)

    return workspace

def create_default_workspace(project_root: Path, interpreter_path: Path) -> dict:
    """Create minimal workspace structure."""
    return {
        "folders": [
            {"path": "."}
        ],
        "settings": {
            "python.defaultInterpreterPath": str(interpreter_path)
        }
    }

def strip_json_comments(content: str) -> str:
    """Remove // and /* */ comments from JSON string."""
    # Simple implementation - may not handle all edge cases
    # VS Code workspace files typically use // comments
    lines = content.split('\n')
    cleaned_lines = []
    for line in lines:
        # Remove // comments
        if '//' in line:
            line = line[:line.index('//')]
        cleaned_lines.append(line)
    return '\n'.join(cleaned_lines)
```

## Acceptance Criteria

### Functional Requirements

- [ ] Discovers .code-workspace files in project
- [ ] Updates python.defaultInterpreterPath setting
- [ ] Preserves other workspace settings
- [ ] Creates new workspace file if none exists
- [ ] Handles multiple workspace files (prompts user)
- [ ] `--workspace` specifies exact file to update
- [ ] `--create` forces new workspace creation
- [ ] `--yes` skips confirmations
- [ ] `--dry-run` shows changes without applying
- [ ] Platform-specific interpreter path (Scripts/python.exe on Windows, bin/python on Unix)
- [ ] Error if project not initialized
- [ ] Error if venv doesn't exist

### Non-Functional Requirements

- [ ] Preserves JSON formatting where possible
- [ ] Handles JSON with comments (VS Code style)
- [ ] Works cross-platform (Windows, macOS, Linux)
- [ ] Clear error messages
- [ ] Test coverage >90%

### Output Requirements

- [ ] Success messages guide user on next steps
- [ ] Confirmation prompts show old vs new values
- [ ] Multiple file selection is intuitive
- [ ] Dry run clearly shows what would change

## Testing Strategy

### Unit Tests (18 tests)

```python
# tests/test_cli/test_configure.py

def test_configure_vscode_updates_workspace(tmp_path):
    """Test that configure vscode updates existing workspace"""

def test_configure_vscode_creates_workspace(tmp_path):
    """Test workspace creation when none exists"""

def test_configure_vscode_preserves_settings(tmp_path):
    """Test that other settings are preserved"""

def test_configure_vscode_multiple_files(tmp_path):
    """Test handling of multiple workspace files"""

def test_configure_vscode_workspace_option(tmp_path):
    """Test --workspace option"""

def test_configure_vscode_create_flag(tmp_path):
    """Test --create flag"""

def test_configure_vscode_not_initialized():
    """Test error when project not initialized"""

def test_configure_vscode_missing_venv(tmp_path):
    """Test error when venv doesn't exist"""

def test_configure_vscode_confirmation(tmp_path):
    """Test confirmation prompt when overwriting"""

def test_configure_vscode_dry_run(tmp_path):
    """Test --dry-run mode"""

# tests/test_utils/test_vscode.py

def test_find_workspace_files_single(tmp_path):
def test_find_workspace_files_multiple(tmp_path):
def test_find_workspace_files_none(tmp_path):

def test_read_workspace_valid(tmp_path):
def test_read_workspace_with_comments(tmp_path):
def test_read_workspace_malformed(tmp_path):

def test_write_workspace(tmp_path):
def test_update_python_interpreter_new():
def test_update_python_interpreter_existing():
def test_create_default_workspace():

def test_strip_json_comments():
def test_interpreter_path_platform_specific():
```

### Integration Tests (3 tests)

```python
def test_init_then_configure_vscode(tmp_path):
    """Test configure after init"""

def test_configure_with_real_workspace_structure(tmp_path):
    """Test with realistic workspace file"""

def test_configure_vscode_full_workflow(tmp_path):
    """Test complete workflow: init, configure, verify"""
```

### Manual Testing Checklist

- [ ] Run `prime-uve configure vscode` in initialized project
- [ ] Verify workspace file created/updated
- [ ] Open workspace in VS Code
- [ ] Verify Python interpreter is correct
- [ ] Test with existing workspace file
- [ ] Test with multiple workspace files
- [ ] Test `--workspace` option
- [ ] Test `--create` flag
- [ ] Test `--dry-run` mode
- [ ] Test on Windows (Scripts/python.exe path)
- [ ] Test on Linux/macOS (bin/python path)

## Design Decisions

### 1. Use python.defaultInterpreterPath Setting

**Decision:** Update `python.defaultInterpreterPath` in workspace settings.

**Rationale:**
- Official VS Code Python extension setting
- Workspace-level (doesn't affect user settings)
- Automatically discovered by IDE
- Supports all IDE features (IntelliSense, debugging, etc.)

### 2. Create Minimal Workspace File

**Decision:** When creating workspace, only include folders and Python interpreter setting.

**Rationale:**
- Minimal configuration reduces maintenance
- Users can add other settings as needed
- Less likely to conflict with project conventions
- Easier to understand generated file

### 3. Preserve Existing Settings

**Decision:** When updating, preserve all other workspace settings.

**Rationale:**
- Users may have customized workspace
- Only modify what's necessary
- Respects existing configuration
- Safe to run multiple times

### 4. Prompt for Multiple Workspace Files

**Decision:** When multiple .code-workspace files found, prompt user to choose.

**Rationale:**
- Ambiguous which file to update
- User knows which workspace they use
- Prevents updating wrong file
- Can be overridden with `--workspace`

### 5. Platform-Specific Interpreter Path

**Decision:** Use Scripts/python.exe on Windows, bin/python on Unix.

**Rationale:**
- Matches venv structure on each platform
- VS Code expects platform-specific paths
- Ensures IDE works correctly

## Risk Assessment

### Medium Risk
- **Malformed JSON** - User-edited workspace could have syntax errors
  - Mitigation: Try to parse, fall back to creating new file with backup

- **JSON comments** - VS Code allows comments, standard JSON doesn't
  - Mitigation: Strip comments before parsing

### Low Risk
- **Multiple workspace files** - User has many workspace files
  - Mitigation: Prompt user to choose, or use `--workspace`

- **Existing interpreter setting** - Could overwrite user's choice
  - Mitigation: Show confirmation before overwriting

## Documentation Requirements

### CLI Help Text

```
prime-uve configure vscode [OPTIONS]

  Update VS Code workspace with venv path.

  This sets the Python interpreter in your workspace settings so VS Code
  can provide IntelliSense, debugging, and other IDE features with your
  external venv.

  If no workspace file exists, one will be created.

Options:
  --workspace PATH         Specific workspace file to update
  --create                 Create new workspace file
  -v, --verbose            Show detailed output
  -y, --yes                Skip confirmation prompts
  --dry-run                Show what would change
  --json                   Output as JSON
  -h, --help               Show this message and exit

Examples:
  prime-uve configure vscode                    # Update or create workspace
  prime-uve configure vscode --workspace myproject.code-workspace
  prime-uve configure vscode --dry-run          # Preview changes
```

### README.md Section

```markdown
## Configure VS Code

Set up VS Code to use your external venv:

```bash
prime-uve configure vscode
```

This updates your workspace settings with the correct Python interpreter path.

### Opening the Workspace

If a workspace file was created:
```bash
code myproject.code-workspace
```

VS Code will automatically use the configured venv for IntelliSense, debugging, and linting.
```

## Success Metrics

- [ ] Successfully updates/creates workspace files
- [ ] VS Code detects interpreter correctly
- [ ] IDE features work (IntelliSense, debugging)
- [ ] Preserves existing settings
- [ ] Handles multiple workspace files gracefully
- [ ] Error messages guide users to fixes
- [ ] Works cross-platform
- [ ] Test coverage >90%

## Next Task Dependencies

This task completes Phase 3: all CLI commands are implemented.

Next phase is Phase 4: Polish and Release
- Task 4.1: Comprehensive Testing
- Task 4.2: Documentation
- Task 4.3: Package and Release

## Estimated Complexity

**Low-Medium** - Straightforward JSON manipulation with some edge case handling.

Estimated effort: 2-3 hours including tests and documentation.
