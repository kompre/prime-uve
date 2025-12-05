# Task 3.5: Implement `prime-uve activate`

## Objective

Implement the `prime-uve activate` command to output shell-specific activation commands for the current project's venv. This command exports all variables from `.env.uve` (not just `UV_PROJECT_ENVIRONMENT`) and activates the venv for the detected shell.

## Context

While `uve` provides transparent venv usage through `uv`, users sometimes need traditional shell activation for:
- IDE integration (PyCharm, VS Code with built-in terminal)
- Shell completion and environment inspection
- Running commands outside uv/uve
- Debugging and development workflows

The command must:
1. Export ALL variables from `.env.uve` (not just UV_PROJECT_ENVIRONMENT)
2. Activate the venv using shell-appropriate commands
3. Support multiple shells (bash, zsh, fish, PowerShell)
4. Handle cross-platform path expansion correctly

## Dependencies

**Required (all complete):**
- Task 1.1: Path generation and variable expansion ✅
- Task 1.3: .env.uve management ✅
- Task 1.4: Project detection ✅
- Task 3.1: CLI framework ✅

**Beneficial:**
- Task 3.2: `prime-uve init` - Creates venvs to activate

## Deliverables

### 1. Implementation Files

**`src/prime_uve/cli/activate.py`** (~200-250 lines)
- Main `activate` command implementation
- Parse all variables from `.env.uve` (not just UV_PROJECT_ENVIRONMENT)
- Generate export commands for all variables
- Generate shell-specific activation commands
- Handle missing `.env.uve` gracefully
- Support `--shell` override

**`src/prime_uve/utils/shell.py`** (~150-200 lines)
- Shell detection logic:
  - `detect_shell() -> str` - Auto-detect from env vars
  - `get_activation_script(shell: str, venv_path: Path) -> str` - Get activation script path
  - `generate_export_command(shell: str, var: str, value: str) -> str` - Generate export syntax
  - `generate_activation_command(shell: str, venv_path: Path) -> str` - Full activation command
- Support shells:
  - bash
  - zsh
  - fish
  - PowerShell (pwsh)
  - cmd (Windows)

### 2. Test Suite

**`tests/test_cli/test_activate.py`** (~18-20 tests)

**Test Categories:**

1. **Basic Functionality** (5 tests)
   - Outputs activation command for current project
   - Exports UV_PROJECT_ENVIRONMENT variable
   - Exports ALL other variables from .env.uve
   - Generates correct venv activation path
   - Works with eval wrapper

2. **Shell Detection** (4 tests)
   - Auto-detects bash from $SHELL
   - Auto-detects zsh from $SHELL
   - Auto-detects fish from $SHELL
   - Auto-detects PowerShell on Windows
   - `--shell` override works

3. **Shell-Specific Output** (5 tests)
   - Bash/Zsh: `export VAR="value"` + `source .../activate`
   - Fish: `set -x VAR "value"` + `source .../activate.fish`
   - PowerShell: `$env:VAR="value"` + `& ...\Activate.ps1`
   - PowerShell ensures HOME is set on Windows
   - All shells export all .env.uve variables

4. **Error Handling** (4 tests)
   - Not in a project (no pyproject.toml)
   - No .env.uve file
   - .env.uve missing UV_PROJECT_ENVIRONMENT
   - Venv doesn't exist (show helpful message)
   - Unsupported shell (with fallback to bash)

5. **Variable Expansion** (2 tests)
   - Expands ${HOME} in venv path for activation
   - Keeps variables unexpanded in export commands
   - Cross-platform HOME handling on Windows

**`tests/test_utils/test_shell.py`** (~15 tests)

1. **Shell Detection** (5 tests)
   - Detect bash from SHELL env var
   - Detect zsh from SHELL env var
   - Detect fish from SHELL env var
   - Detect PowerShell on Windows (SHELL not set)
   - Detect cmd on Windows (fallback)

2. **Export Commands** (5 tests)
   - Generate bash export: `export VAR="value"`
   - Generate zsh export: `export VAR="value"`
   - Generate fish export: `set -x VAR "value"`
   - Generate PowerShell export: `$env:VAR="value"`
   - Escape special characters in values

3. **Activation Scripts** (5 tests)
   - Bash activation script path: `bin/activate`
   - Fish activation script path: `bin/activate.fish`
   - PowerShell activation script path: `Scripts/Activate.ps1`
   - Windows cmd activation script path: `Scripts/activate.bat`
   - Cross-platform path handling

### 3. Integration Points

**CLI Command Registration** (in `main.py`):
```python
from prime_uve.cli import activate

@cli.command()
@click.option('--shell', type=str, help='Shell type (bash, zsh, fish, pwsh)')
@common_options
@handle_errors
def activate_cmd(ctx, shell, verbose, yes, dry_run, json_output):
    """Output activation command for current venv."""
    from prime_uve.cli.activate import activate_command
    activate_command(ctx, shell, verbose, yes, dry_run, json_output)
```

## Command Specification

### Usage

```bash
eval "$(prime-uve activate)"
```

Or with shell override:
```bash
eval "$(prime-uve activate --shell bash)"
```

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--shell SHELL` | | auto-detect | Override shell detection (bash, zsh, fish, pwsh) |
| `--verbose` | `-v` | False | Show detailed output (to stderr) |

**Note:** `--json`, `--yes`, `--dry-run` are not applicable to this command.

### Output Examples

**Bash/Zsh output:**
```bash
export UV_PROJECT_ENVIRONMENT="${HOME}/prime-uve/venvs/myproject_a1b2c3d4"
export DATABASE_URL="postgresql://localhost/mydb"
export API_KEY="secret123"
source /home/user/prime-uve/venvs/myproject_a1b2c3d4/bin/activate
```

**Fish output:**
```fish
set -x UV_PROJECT_ENVIRONMENT "$HOME/prime-uve/venvs/myproject_a1b2c3d4"
set -x DATABASE_URL "postgresql://localhost/mydb"
set -x API_KEY "secret123"
source /home/user/prime-uve/venvs/myproject_a1b2c3d4/bin/activate.fish
```

**PowerShell output:**
```powershell
if (-not $env:HOME) { $env:HOME = $env:USERPROFILE }
$env:UV_PROJECT_ENVIRONMENT="${HOME}/prime-uve/venvs/myproject_a1b2c3d4"
$env:DATABASE_URL="postgresql://localhost/mydb"
$env:API_KEY="secret123"
& C:\Users\user\prime-uve\venvs\myproject_a1b2c3d4\Scripts\Activate.ps1
```

**Windows CMD output:**
```cmd
set HOME=%USERPROFILE%
set UV_PROJECT_ENVIRONMENT=%HOME%\prime-uve\venvs\myproject_a1b2c3d4
set DATABASE_URL=postgresql://localhost/mydb
set API_KEY=secret123
call C:\Users\user\prime-uve\venvs\myproject_a1b2c3d4\Scripts\activate.bat
```

**Verbose mode (to stderr):**
```
[INFO] Detected shell: bash
[INFO] Project: myproject
[INFO] Venv: ${HOME}/prime-uve/venvs/myproject_a1b2c3d4
[INFO] Expanded: /home/user/prime-uve/venvs/myproject_a1b2c3d4
[INFO] Exporting 3 variables from .env.uve
[INFO] Activation script: /home/user/prime-uve/venvs/myproject_a1b2c3d4/bin/activate
```

**Error (not in project):**
```
Error: Not in a Python project
Could not find pyproject.toml in current directory or any parent directory.

Run 'prime-uve activate' from within a project directory.
```

**Error (no .env.uve):**
```
Error: Project not initialized
No .env.uve file found.

Run 'prime-uve init' to initialize the project.
```

**Error (venv doesn't exist):**
```
Error: Venv not found
Expected venv at: /home/user/prime-uve/venvs/myproject_a1b2c3d4

The venv may have been deleted. To recreate:
  prime-uve init --force
```

## Implementation Logic

### Main Flow

```python
def activate_command(ctx, shell_override, verbose, yes, dry_run, json_output):
    # 1. Find project root
    project_root = find_project_root()
    if not project_root:
        raise ValueError(
            "Not in a Python project\n"
            "Could not find pyproject.toml in current directory or any parent directory."
        )

    # 2. Find and read .env.uve
    env_file = find_env_file(project_root)
    if not env_file or not env_file.exists():
        raise ValueError(
            "Project not initialized\n"
            "No .env.uve file found.\n\n"
            "Run 'prime-uve init' to initialize the project."
        )

    env_vars = read_env_file(env_file)
    if not env_vars:
        raise ValueError(
            "Empty .env.uve file\n"
            "Run 'prime-uve init' to configure the project."
        )

    # 3. Extract venv path and validate
    venv_path_var = env_vars.get("UV_PROJECT_ENVIRONMENT")
    if not venv_path_var:
        raise ValueError(
            ".env.uve missing UV_PROJECT_ENVIRONMENT\n"
            "Run 'prime-uve init --force' to reconfigure."
        )

    venv_path_expanded = expand_path_variables(venv_path_var)

    if not venv_path_expanded.exists():
        raise ValueError(
            f"Venv not found\n"
            f"Expected venv at: {venv_path_expanded}\n\n"
            f"The venv may have been deleted. To recreate:\n"
            f"  prime-uve init --force"
        )

    # 4. Detect or use shell override
    shell = shell_override or detect_shell()

    if verbose:
        echo(f"[INFO] Detected shell: {shell}", err=True)
        echo(f"[INFO] Project: {get_project_metadata(project_root).get('name', 'unknown')}", err=True)
        echo(f"[INFO] Venv: {venv_path_var}", err=True)
        echo(f"[INFO] Expanded: {venv_path_expanded}", err=True)
        echo(f"[INFO] Exporting {len(env_vars)} variables from .env.uve", err=True)

    # 5. Generate activation commands
    commands = []

    # On Windows PowerShell, ensure HOME is set first
    if shell in ("pwsh", "powershell") and sys.platform == "win32":
        commands.append('if (-not $env:HOME) { $env:HOME = $env:USERPROFILE }')

    # Export all variables from .env.uve
    for var_name, var_value in env_vars.items():
        export_cmd = generate_export_command(shell, var_name, var_value)
        commands.append(export_cmd)

    # Activation command
    activation_cmd = generate_activation_command(shell, venv_path_expanded)
    commands.append(activation_cmd)

    # 6. Output commands
    for cmd in commands:
        echo(cmd)
```

### Shell Detection

```python
def detect_shell() -> str:
    """Detect current shell from environment variables."""
    import os
    import sys

    # Check SHELL env var (Unix)
    shell_path = os.environ.get("SHELL", "")
    if shell_path:
        shell_name = os.path.basename(shell_path)
        if "bash" in shell_name:
            return "bash"
        elif "zsh" in shell_name:
            return "zsh"
        elif "fish" in shell_name:
            return "fish"

    # Windows detection
    if sys.platform == "win32":
        # Check if running in PowerShell
        if os.environ.get("PSModulePath"):
            return "pwsh"
        # Fallback to cmd
        return "cmd"

    # Default fallback
    return "bash"
```

### Export Command Generation

```python
def generate_export_command(shell: str, var_name: str, var_value: str) -> str:
    """Generate shell-specific export command.

    IMPORTANT: Keep variables unexpanded (e.g., ${HOME} stays as ${HOME}).
    Only the activation script path gets expanded.
    """
    # Escape special characters in value
    value_escaped = escape_shell_value(var_value, shell)

    if shell in ("bash", "zsh"):
        return f'export {var_name}="{value_escaped}"'
    elif shell == "fish":
        return f'set -x {var_name} "{value_escaped}"'
    elif shell in ("pwsh", "powershell"):
        return f'$env:{var_name}="{value_escaped}"'
    elif shell == "cmd":
        # CMD uses % for variables, not $
        # Replace ${HOME} with %HOME%
        value_cmd = value_escaped.replace("${HOME}", "%HOME%").replace("$HOME", "%HOME%")
        return f'set {var_name}={value_cmd}'
    else:
        # Fallback to bash syntax
        return f'export {var_name}="{value_escaped}"'

def escape_shell_value(value: str, shell: str) -> str:
    """Escape special characters for shell."""
    if shell in ("bash", "zsh", "fish"):
        # Escape double quotes and backslashes
        return value.replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$')
    elif shell in ("pwsh", "powershell"):
        # Escape double quotes
        return value.replace('"', '`"')
    elif shell == "cmd":
        # CMD has minimal escaping needs
        return value
    return value
```

### Activation Command Generation

```python
def generate_activation_command(shell: str, venv_path: Path) -> str:
    """Generate shell-specific venv activation command.

    venv_path is the EXPANDED path (variables already resolved).
    """
    if shell in ("bash", "zsh"):
        activate_script = venv_path / "bin" / "activate"
        return f"source {activate_script}"

    elif shell == "fish":
        activate_script = venv_path / "bin" / "activate.fish"
        return f"source {activate_script}"

    elif shell in ("pwsh", "powershell"):
        activate_script = venv_path / "Scripts" / "Activate.ps1"
        # Use & operator for PowerShell
        return f"& {activate_script}"

    elif shell == "cmd":
        activate_script = venv_path / "Scripts" / "activate.bat"
        return f"call {activate_script}"

    else:
        # Fallback to bash
        activate_script = venv_path / "bin" / "activate"
        return f"source {activate_script}"
```

## Acceptance Criteria

### Functional Requirements

- [ ] Detects shell automatically (bash, zsh, fish, PowerShell, cmd)
- [ ] `--shell` override allows manual shell selection
- [ ] Exports ALL variables from `.env.uve` (not just UV_PROJECT_ENVIRONMENT)
- [ ] Variables exported with unexpanded form (${HOME} stays ${HOME})
- [ ] Activation script path uses expanded path
- [ ] Generates correct export syntax for each shell
- [ ] Generates correct activation command for each shell
- [ ] Works with `eval "$(prime-uve activate)"`
- [ ] PowerShell output ensures HOME is set on Windows
- [ ] Handles missing .env.uve gracefully
- [ ] Handles missing venv gracefully
- [ ] Verbose mode shows diagnostic info to stderr

### Non-Functional Requirements

- [ ] Output is directly eval-able (no extra formatting)
- [ ] Errors go to stderr, not stdout
- [ ] Works cross-platform (Windows, macOS, Linux)
- [ ] Handles special characters in variable values
- [ ] Test coverage >90%

### Output Requirements

- [ ] Clean command output to stdout
- [ ] Verbose output to stderr (doesn't interfere with eval)
- [ ] Error messages to stderr with helpful guidance
- [ ] No extra whitespace or formatting

## Testing Strategy

### Unit Tests (20 tests)

```python
# tests/test_cli/test_activate.py

def test_activate_bash_output(tmp_path):
    """Test activate generates correct bash commands"""

def test_activate_zsh_output(tmp_path):
    """Test activate generates correct zsh commands"""

def test_activate_fish_output(tmp_path):
    """Test activate generates correct fish commands"""

def test_activate_powershell_output(tmp_path):
    """Test activate generates correct PowerShell commands"""

def test_activate_exports_all_env_vars(tmp_path):
    """Test that ALL variables from .env.uve are exported"""

def test_activate_shell_override(tmp_path):
    """Test --shell override works"""

def test_activate_not_in_project():
    """Test error when not in a project"""

def test_activate_no_env_file(tmp_path):
    """Test error when .env.uve doesn't exist"""

def test_activate_missing_venv(tmp_path):
    """Test error when venv doesn't exist"""

def test_activate_empty_env_file(tmp_path):
    """Test error when .env.uve is empty"""

def test_activate_verbose_mode(tmp_path):
    """Test --verbose shows diagnostic info"""

# tests/test_utils/test_shell.py

def test_detect_shell_bash():
def test_detect_shell_zsh():
def test_detect_shell_fish():
def test_detect_shell_powershell_windows():
def test_detect_shell_default_fallback():

def test_export_command_bash():
def test_export_command_fish():
def test_export_command_powershell():
def test_export_command_escaping():

def test_activation_command_bash():
def test_activation_command_fish():
def test_activation_command_powershell():
def test_activation_command_windows_cmd():

def test_escape_special_characters():
def test_activation_script_paths():
```

### Integration Tests (4 tests)

```python
def test_init_then_activate(tmp_path):
    """Test activate works after init"""

def test_activate_eval_workflow(tmp_path):
    """Test that output can be eval'd successfully"""

def test_activate_with_multiple_env_vars(tmp_path):
    """Test exporting multiple variables"""

def test_activate_cross_platform_paths(tmp_path):
    """Test path handling on Windows and Unix"""
```

### Manual Testing Checklist

- [ ] Run `eval "$(prime-uve activate)"` in bash
- [ ] Verify venv activates and prompt changes
- [ ] Check that `echo $UV_PROJECT_ENVIRONMENT` shows correct path
- [ ] Check that all .env.uve variables are exported
- [ ] Test in zsh shell
- [ ] Test in fish shell
- [ ] Test in PowerShell on Windows
- [ ] Test `--shell bash` override
- [ ] Test error when not in project
- [ ] Test verbose mode output

## Design Decisions

### 1. Export All Variables, Not Just UV_PROJECT_ENVIRONMENT

**Decision:** Export every variable in `.env.uve`, not only UV_PROJECT_ENVIRONMENT.

**Rationale:**
- Users may add other environment variables to `.env.uve`
- Activation should fully replicate the uve environment
- Matches user expectations (activate = full env setup)
- Enables .env.uve as single source of env config

### 2. Keep Variables Unexpanded in Exports

**Decision:** Export variables with their variable form (${HOME}), not expanded paths.

**Rationale:**
- Consistent with .env.uve storage format
- Works correctly when shared across machines
- Shell expands variables at runtime
- Only activation script path needs expansion (to check existence)

### 3. Output Commands to Stdout, Info to Stderr

**Decision:** All activation commands to stdout, verbose/error messages to stderr.

**Rationale:**
- Enables `eval "$(prime-uve activate)"` pattern
- Verbose mode doesn't break eval
- Standard Unix convention

### 4. Auto-Detect Shell with Override Option

**Decision:** Detect shell automatically, provide `--shell` for manual override.

**Rationale:**
- Works out of the box for most users
- Power users can override when needed (scripts, etc.)
- No configuration file needed

### 5. Ensure HOME on Windows for PowerShell

**Decision:** PowerShell output includes `if (-not $env:HOME) { $env:HOME = $env:USERPROFILE }`.

**Rationale:**
- Ensures ${HOME} variable expansion works
- Matches uve wrapper behavior
- Cross-platform consistency

## Risk Assessment

### Medium Risk
- **Shell detection inaccuracy** - Might detect wrong shell
  - Mitigation: Provide `--shell` override, default to bash (safest)

- **Special characters in env values** - Could break shell commands
  - Mitigation: Proper escaping for each shell

### Low Risk
- **Unsupported shells** - User has exotic shell
  - Mitigation: Fall back to bash syntax, document supported shells

- **Venv activation script missing** - Corrupted venv
  - Mitigation: Check existence, suggest reinit

## Documentation Requirements

### CLI Help Text

```
prime-uve activate [OPTIONS]

  Output activation command for current project's venv.

  This command generates shell-specific commands to:
    • Export all variables from .env.uve
    • Activate the project's venv

  Usage:
    eval "$(prime-uve activate)"

  Supported shells:
    • bash, zsh (Linux, macOS, WSL)
    • fish (Linux, macOS)
    • PowerShell (Windows, cross-platform)
    • cmd (Windows)

Options:
  --shell SHELL         Override shell detection (bash, zsh, fish, pwsh, cmd)
  -v, --verbose         Show diagnostic output (to stderr)
  -h, --help            Show this message and exit

Examples:
  eval "$(prime-uve activate)"           # Bash/Zsh
  eval (prime-uve activate | psub)       # Fish
  Invoke-Expression (prime-uve activate) # PowerShell

  prime-uve activate --shell bash        # Force bash syntax
```

### README.md Section

```markdown
## Activate the Virtual Environment

Activate the venv in your shell:

**Bash/Zsh:**
```bash
eval "$(prime-uve activate)"
```

**Fish:**
```fish
eval (prime-uve activate | psub)
```

**PowerShell:**
```powershell
Invoke-Expression (prime-uve activate)
```

This exports all variables from `.env.uve` and activates the venv.

### Shell Detection

`prime-uve activate` auto-detects your shell. To override:
```bash
eval "$(prime-uve activate --shell bash)"
```


## Success Metrics

- [ ] Generates correct commands for all supported shells
- [ ] Works with `eval "$(...)"`pattern
- [ ] Exports all .env.uve variables
- [ ] Variables correctly exported with unexpanded form
- [ ] Activation script path correctly expanded
- [ ] Shell detection works reliably
- [ ] Error messages are helpful
- [ ] Test coverage >90%
- [ ] Works cross-platform

## Next Task Dependencies

This task is independent of:
- Task 3.6: `prime-uve configure vscode` (different integration approach)

## Estimated Complexity

**Medium** - Shell integration requires careful handling of different syntaxes, but logic is straightforward.

Estimated effort: 3-4 hours including tests and documentation.

---

## Progress Log

### 2025-12-05 - Work Started
- Moved to pending and created feature branch `feature/prime-uve-activate`
- Ready to begin implementation

### 2025-12-05 - Implementation Complete
- Implemented `src/prime_uve/utils/shell.py` with shell detection and command generation
- Implemented `src/prime_uve/cli/activate.py` with full activate command logic
- Registered activate command in `src/prime_uve/cli/main.py`
- Created comprehensive test suites:
  - 32 tests for shell utilities (test_utils/test_shell.py)
  - 18 tests for activate command (test_cli/test_activate.py)
- All tests passing: 346 tests total, 8 skipped
- Updated CLAUDE.md with improved task workflow documentation
- Ready for PR
