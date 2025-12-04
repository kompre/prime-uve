# Task 3.3: Implement `prime-uve list`

## Objective

Implement the `prime-uve list` command to display all managed venvs with validation status. This command provides visibility into tracked projects, their venv locations, and whether the mappings are still valid.

## Context

This is a diagnostic and information command that helps users:
- See all projects managed by prime-uve
- Identify orphaned venvs (project deleted or moved)
- Detect path mismatches (cache vs .env.uve disagreement)
- Get quick overview of disk usage

## Dependencies

**Required (all complete):**
- Task 1.1: Path hashing ✅
- Task 1.2: Cache system ✅
- Task 1.3: .env.uve management ✅
- Task 1.4: Project detection ✅
- Task 3.1: CLI framework ✅

**Beneficial but not required:**
- Task 3.2: `prime-uve init` - Provides data to list

## Deliverables

### 1. Implementation Files

**`src/prime_uve/cli/list.py`** (~200-250 lines)
- Main `list` command implementation
- Validation logic for each cached project:
  - Project directory exists
  - Venv directory exists
  - `.env.uve` exists and contains matching path
- Table formatting for terminal output
- JSON formatting for machine-readable output
- Statistics summary (total, valid, orphaned, mismatched)

**`src/prime_uve/core/validation.py`** (~150 lines)
- Validation utilities:
  - `ValidationResult` dataclass with status and details
  - `validate_project_mapping(project_path, cache_entry) -> ValidationResult`
  - `validate_all_mappings(cache) -> list[ValidationResult]`
  - `get_disk_usage(venv_path) -> int` - Calculate venv size
- Status types:
  - `VALID` - Everything matches and exists
  - `PROJECT_MISSING` - Project directory deleted
  - `VENV_MISSING` - Venv directory doesn't exist
  - `PATH_MISMATCH` - .env.uve has different path than cache
  - `ENV_FILE_MISSING` - .env.uve file not found

### 2. Test Suite

**`tests/test_cli/test_list.py`** (~18-20 tests)

**Test Categories:**

1. **Basic Functionality** (4 tests)
   - Empty cache shows helpful message
   - Single valid project listed correctly
   - Multiple projects listed correctly
   - Table formatting is correct

2. **Validation States** (5 tests)
   - Valid project shows ✓ status
   - Project missing shows ✗ status
   - Venv missing shows ⚠ status
   - Path mismatch shows ⚠ status
   - .env.uve missing shows ⚠ status

3. **Filtering** (3 tests)
   - `--orphan-only` shows only invalid entries
   - `--orphan-only` with no orphans shows message
   - `--valid-only` shows only valid entries

4. **Output Formats** (4 tests)
   - Table output formatting
   - `--json` outputs valid JSON
   - `--json` with empty cache
   - `--verbose` shows additional details

5. **Statistics** (2 tests)
   - Summary shows correct counts (total, valid, orphaned)
   - Disk usage calculation (when `--verbose`)

**`tests/test_core/test_validation.py`** (~12 tests)

1. **Validation Logic** (8 tests)
   - Validate valid project mapping
   - Detect missing project directory
   - Detect missing venv directory
   - Detect path mismatch
   - Detect missing .env.uve file
   - Handle malformed .env.uve
   - Handle permission errors
   - Validate all mappings at once

2. **Disk Usage** (4 tests)
   - Calculate venv disk usage
   - Handle missing directory
   - Handle permission errors
   - Format human-readable sizes

### 3. Integration Points

**CLI Command Registration** (in `main.py`):
```python
from prime_uve.cli import list as list_module

@cli.command(name='list')
@click.option('--orphan-only', is_flag=True, help='Show only orphaned venvs')
@click.option('--valid-only', is_flag=True, help='Show only valid venvs')
@common_options
@handle_errors
def list_cmd(ctx, orphan_only, valid_only, verbose, yes, dry_run, json_output):
    """List all managed venvs with validation status."""
    from prime_uve.cli.list import list_command
    list_command(ctx, orphan_only, valid_only, verbose, yes, dry_run, json_output)
```

## Command Specification

### Usage

```bash
prime-uve list [OPTIONS]
```

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--orphan-only` | | False | Show only orphaned/invalid venvs |
| `--valid-only` | | False | Show only valid venvs |
| `--verbose` | `-v` | False | Show additional details (disk usage, paths) |
| `--json` | | False | Output as JSON |

### Output Examples

**Success (table format - normal):**
```
Managed Virtual Environments

PROJECT             VENV PATH                        STATUS
─────────────────────────────────────────────────────────────────────────
myproject           ~/prime-uve/venvs/myproj_a1b2    ✓ Valid
another-project     ~/prime-uve/venvs/anothe_c3d4    ✓ Valid
old-project         ~/prime-uve/venvs/oldpro_e5f6    ✗ Project deleted
broken-project      ~/prime-uve/venvs/broken_g7h8    ⚠ Path mismatch

Summary: 4 total, 2 valid, 1 orphaned, 1 mismatch
```

**Success (table format - verbose):**
```
Managed Virtual Environments

PROJECT             VENV PATH                        SIZE      STATUS
────────────────────────────────────────────────────────────────────────────
myproject           ~/prime-uve/venvs/myproj_a1b2    125 MB    ✓ Valid
  Project: /home/user/projects/myproject
  Venv:    /home/user/prime-uve/venvs/myproject_a1b2c3d4
  Hash:    a1b2c3d4
  Created: 2025-12-01 10:30:45

another-project     ~/prime-uve/venvs/anothe_c3d4    89 MB     ✓ Valid
  Project: /home/user/projects/another-project
  Venv:    /home/user/prime-uve/venvs/another-project_c3d4e5f6
  Hash:    c3d4e5f6
  Created: 2025-12-02 14:22:10

old-project         ~/prime-uve/venvs/oldpro_e5f6    0 B       ✗ Project deleted
  Project: /home/user/projects/old-project (NOT FOUND)
  Venv:    /home/user/prime-uve/venvs/old-project_e5f6g7h8 (exists)

broken-project      ~/prime-uve/venvs/broken_g7h8    156 MB    ⚠ Path mismatch
  Cache:     ${HOME}/prime-uve/venvs/broken-project_g7h8i9j0
  .env.uve:  ${HOME}/prime-uve/venvs/broken-project_k1l2m3n4
  Reason:    Project may have been reinitialized with --force

Summary: 4 total, 2 valid, 1 orphaned, 1 mismatch
Total disk usage: 370 MB
```

**Success (--orphan-only):**
```
Orphaned Virtual Environments

PROJECT             VENV PATH                        STATUS
────────────────────────────────────────────────────────────────────────
old-project         ~/prime-uve/venvs/oldpro_e5f6    ✗ Project deleted

Found 1 orphaned venv. Run 'prime-uve prune --orphan' to clean up.
```

**Success (--json):**
```json
{
  "venvs": [
    {
      "project_name": "myproject",
      "project_path": "/home/user/projects/myproject",
      "venv_path": "${HOME}/prime-uve/venvs/myproject_a1b2c3d4",
      "venv_path_expanded": "/home/user/prime-uve/venvs/myproject_a1b2c3d4",
      "hash": "a1b2c3d4",
      "created_at": "2025-12-01T10:30:45Z",
      "status": "valid",
      "validation": {
        "project_exists": true,
        "venv_exists": true,
        "env_file_exists": true,
        "paths_match": true
      },
      "disk_usage_bytes": 131072000
    },
    {
      "project_name": "old-project",
      "project_path": "/home/user/projects/old-project",
      "venv_path": "${HOME}/prime-uve/venvs/old-project_e5f6g7h8",
      "venv_path_expanded": "/home/user/prime-uve/venvs/old-project_e5f6g7h8",
      "hash": "e5f6g7h8",
      "created_at": "2025-11-15T09:12:33Z",
      "status": "project_missing",
      "validation": {
        "project_exists": false,
        "venv_exists": true,
        "env_file_exists": false,
        "paths_match": false
      },
      "disk_usage_bytes": 0
    }
  ],
  "summary": {
    "total": 2,
    "valid": 1,
    "orphaned": 1,
    "mismatched": 0,
    "total_disk_usage_bytes": 131072000
  }
}
```

**Empty cache:**
```
No managed virtual environments found.

Run 'prime-uve init' in a project directory to get started.
```

**Empty cache (--json):**
```json
{
  "venvs": [],
  "summary": {
    "total": 0,
    "valid": 0,
    "orphaned": 0,
    "mismatched": 0,
    "total_disk_usage_bytes": 0
  }
}
```

## Implementation Logic

### Main Flow

```python
def list_command(ctx, orphan_only, valid_only, verbose, yes, dry_run, json_output):
    # 1. Load cache
    cache = Cache()
    mappings = cache.list_all()

    if not mappings:
        if json_output:
            output_json({"venvs": [], "summary": {...}})
        else:
            info("No managed virtual environments found.")
            echo("Run 'prime-uve init' in a project directory to get started.")
        return

    # 2. Validate all mappings
    results = []
    for project_path, cache_entry in mappings.items():
        result = validate_project_mapping(project_path, cache_entry)
        results.append(result)

    # 3. Filter if requested
    if orphan_only:
        results = [r for r in results if r.status != ValidationStatus.VALID]
    elif valid_only:
        results = [r for r in results if r.status == ValidationStatus.VALID]

    # 4. Calculate statistics
    stats = {
        "total": len(mappings),
        "valid": sum(1 for r in results if r.status == ValidationStatus.VALID),
        "orphaned": sum(1 for r in results if r.status == ValidationStatus.PROJECT_MISSING),
        "mismatched": sum(1 for r in results if r.status == ValidationStatus.PATH_MISMATCH),
        "total_disk_usage": sum(get_disk_usage(r.venv_path_expanded) for r in results)
    }

    # 5. Output
    if json_output:
        output_json_list(results, stats)
    else:
        output_table(results, stats, verbose)

        # Helpful tip for orphans
        if stats["orphaned"] > 0:
            echo(f"\nFound {stats['orphaned']} orphaned venv(s). "
                 f"Run 'prime-uve prune --orphan' to clean up.")
```

### Validation Logic

```python
@dataclass
class ValidationResult:
    project_name: str
    project_path: Path
    venv_path: str  # Variable form
    venv_path_expanded: Path  # Actual path
    hash: str
    created_at: str
    status: ValidationStatus
    details: dict
    disk_usage_bytes: int

def validate_project_mapping(project_path: str, cache_entry: dict) -> ValidationResult:
    project_path = Path(project_path)
    venv_path = cache_entry["venv_path"]
    venv_path_expanded = expand_path_variables(venv_path)

    details = {
        "project_exists": project_path.exists(),
        "venv_exists": venv_path_expanded.exists(),
        "env_file_exists": False,
        "paths_match": False
    }

    # Check .env.uve
    env_file = project_path / ".env.uve"
    if env_file.exists():
        details["env_file_exists"] = True
        try:
            env_vars = read_env_file(env_file)
            env_venv_path = env_vars.get("UV_PROJECT_ENVIRONMENT")
            details["paths_match"] = env_venv_path == venv_path
        except Exception:
            pass

    # Determine status
    if not details["project_exists"]:
        status = ValidationStatus.PROJECT_MISSING
    elif not details["venv_exists"]:
        status = ValidationStatus.VENV_MISSING
    elif not details["env_file_exists"]:
        status = ValidationStatus.ENV_FILE_MISSING
    elif not details["paths_match"]:
        status = ValidationStatus.PATH_MISMATCH
    else:
        status = ValidationStatus.VALID

    # Get disk usage (only if venv exists)
    disk_usage = 0
    if details["venv_exists"]:
        try:
            disk_usage = get_disk_usage(venv_path_expanded)
        except Exception:
            pass

    return ValidationResult(
        project_name=cache_entry["project_name"],
        project_path=project_path,
        venv_path=venv_path,
        venv_path_expanded=venv_path_expanded,
        hash=cache_entry["path_hash"],
        created_at=cache_entry["created_at"],
        status=status,
        details=details,
        disk_usage_bytes=disk_usage
    )
```

### Table Formatting

```python
def output_table(results: list[ValidationResult], stats: dict, verbose: bool):
    echo("Managed Virtual Environments\n")

    if verbose:
        # Wide format with disk usage
        for result in results:
            status_symbol = get_status_symbol(result.status)
            status_text = get_status_text(result.status)
            size = format_bytes(result.disk_usage_bytes)

            # Truncate paths for readability
            venv_short = truncate_path(result.venv_path, 32)

            echo(f"{result.project_name:<20} {venv_short:<32} {size:<10} {status_symbol} {status_text}")

            # Extra details in verbose mode
            echo(f"  Project: {result.project_path}")
            echo(f"  Venv:    {result.venv_path_expanded}")
            echo(f"  Hash:    {result.hash}")
            echo(f"  Created: {result.created_at}")

            if result.status != ValidationStatus.VALID:
                echo(f"  Issue:   {result.details}")
            echo()
    else:
        # Compact format
        header = f"{'PROJECT':<20} {'VENV PATH':<32} {'STATUS'}"
        echo(header)
        echo("─" * len(header))

        for result in results:
            status_symbol = get_status_symbol(result.status)
            status_text = get_status_text(result.status)
            venv_short = truncate_path(result.venv_path, 32)

            echo(f"{result.project_name:<20} {venv_short:<32} {status_symbol} {status_text}")

    # Summary
    echo(f"\nSummary: {stats['total']} total, {stats['valid']} valid, "
         f"{stats['orphaned']} orphaned, {stats['mismatched']} mismatch")

    if verbose and stats['total_disk_usage'] > 0:
        total_size = format_bytes(stats['total_disk_usage'])
        echo(f"Total disk usage: {total_size}")
```

## Acceptance Criteria

### Functional Requirements

- [ ] Lists all projects tracked in cache
- [ ] Validates each project mapping
- [ ] Shows correct status symbols (✓/✗/⚠)
- [ ] Detects missing project directories
- [ ] Detects missing venv directories
- [ ] Detects .env.uve path mismatches
- [ ] `--orphan-only` filters to invalid entries only
- [ ] `--valid-only` filters to valid entries only
- [ ] `--verbose` shows extended information and disk usage
- [ ] `--json` outputs machine-readable JSON
- [ ] Empty cache shows helpful message
- [ ] Summary statistics are accurate

### Non-Functional Requirements

- [ ] Performance: Lists 100+ projects in <1 second
- [ ] Table formatting is readable and aligned
- [ ] Paths are truncated intelligently (show most relevant parts)
- [ ] Works cross-platform (Windows, macOS, Linux)
- [ ] Handles permission errors gracefully
- [ ] Test coverage >90%

### Output Requirements

- [ ] Table columns are aligned
- [ ] Paths are shortened to fit terminal width
- [ ] Status symbols are colored (green ✓, red ✗, yellow ⚠)
- [ ] Summary line shows counts
- [ ] Verbose mode shows full paths and details
- [ ] JSON output is valid and parseable
- [ ] Helpful tips when orphans detected

## Testing Strategy

### Unit Tests (20 tests)

```python
# tests/test_cli/test_list.py

def test_list_empty_cache():
    """Test list with empty cache shows helpful message"""

def test_list_single_valid_project(tmp_path):
    """Test list with one valid project"""

def test_list_multiple_projects(tmp_path):
    """Test list with multiple projects"""

def test_list_orphaned_project(tmp_path):
    """Test list detects missing project directory"""

def test_list_missing_venv(tmp_path):
    """Test list detects missing venv directory"""

def test_list_path_mismatch(tmp_path):
    """Test list detects .env.uve path mismatch"""

def test_list_orphan_only_filter(tmp_path):
    """Test --orphan-only shows only invalid entries"""

def test_list_valid_only_filter(tmp_path):
    """Test --valid-only shows only valid entries"""

def test_list_verbose_mode(tmp_path):
    """Test --verbose shows extended information"""

def test_list_json_output(tmp_path):
    """Test --json outputs valid JSON"""

def test_list_table_formatting():
    """Test table column alignment and formatting"""

def test_list_path_truncation():
    """Test long paths are truncated intelligently"""

def test_list_statistics_accuracy(tmp_path):
    """Test summary statistics are correct"""

# tests/test_core/test_validation.py

def test_validate_valid_project(tmp_path):
    """Test validation of valid project mapping"""

def test_validate_missing_project(tmp_path):
    """Test detection of missing project directory"""

def test_validate_missing_venv(tmp_path):
    """Test detection of missing venv directory"""

def test_validate_path_mismatch(tmp_path):
    """Test detection of .env.uve path mismatch"""

def test_validate_missing_env_file(tmp_path):
    """Test detection of missing .env.uve file"""

def test_validate_permission_error(tmp_path, mocker):
    """Test handling of permission errors"""

def test_disk_usage_calculation(tmp_path):
    """Test disk usage calculation"""

def test_format_bytes():
    """Test human-readable byte formatting"""
```

### Integration Tests (3 tests)

```python
def test_list_after_init(tmp_path):
    """Test that list shows project after init"""
    # Run init, then list, verify entry appears

def test_list_after_project_deleted(tmp_path):
    """Test that list detects deleted project"""
    # Run init, delete project, run list, verify orphan status

def test_list_with_multiple_states(tmp_path):
    """Test list with mix of valid/invalid/mismatched projects"""
```

### Manual Testing Checklist

- [ ] Run `prime-uve list` with empty cache
- [ ] Initialize project, verify it appears in list
- [ ] Delete project, verify orphan status
- [ ] Test `--orphan-only` filter
- [ ] Test `--valid-only` filter
- [ ] Test `--verbose` mode
- [ ] Test `--json` output
- [ ] Verify table formatting on different terminal widths
- [ ] Test with 10+ projects
- [ ] Verify disk usage calculations

## Design Decisions

### 1. Validation Status Types

**Decision:** Use 5 distinct status types: VALID, PROJECT_MISSING, VENV_MISSING, ENV_FILE_MISSING, PATH_MISMATCH.

**Rationale:**
- Provides granular diagnostic information
- Helps user understand specific issue
- Enables targeted fixes

### 2. Show Orphaned Count Even When Not Filtering

**Decision:** Always show orphan count in summary, with tip to run `prune --orphan`.

**Rationale:**
- Proactive maintenance guidance
- Helps users discover cleanup opportunities
- Non-intrusive (just a tip, not a warning)

### 3. Truncate Paths in Compact Mode

**Decision:** Show shortened paths in normal mode, full paths in verbose mode.

**Rationale:**
- Improves readability on narrow terminals
- Full paths available when needed via --verbose
- Balances brevity and completeness

### 4. Calculate Disk Usage Only in Verbose Mode

**Decision:** Skip disk usage calculation in normal mode, calculate in verbose mode.

**Rationale:**
- Performance - walking directory tree can be slow
- Most users don't need this information regularly
- Available when needed

### 5. Default to Showing All (No Filter)

**Decision:** By default, show all projects regardless of status.

**Rationale:**
- Complete visibility into managed venvs
- Users can easily filter if needed
- Matches common CLI tool behavior (ls, docker ps, etc.)

## Risk Assessment

### Medium Risk
- **Performance with many projects** - Validation could be slow with 100+ projects
  - Mitigation: Parallelize validation, add progress indicator if slow

- **Very long paths** - Could break table formatting
  - Mitigation: Intelligent truncation, full paths in verbose mode

### Low Risk
- **Permission errors** - Some directories might not be readable
  - Mitigation: Catch exceptions, mark as "unknown" status

- **Concurrent modifications** - Cache could change during listing
  - Mitigation: Read cache once at start, acceptable staleness

## Documentation Requirements

### CLI Help Text

```
prime-uve list [OPTIONS]

  List all managed virtual environments with validation status.

  Validation checks:
    • Project directory exists
    • Venv directory exists
    • .env.uve file exists
    • .env.uve path matches cache

  Status symbols:
    ✓ Valid      - Everything is correct
    ✗ Orphaned   - Project deleted or venv missing
    ⚠ Mismatch   - .env.uve doesn't match cache

Options:
  --orphan-only          Show only orphaned/invalid venvs
  --valid-only           Show only valid venvs
  -v, --verbose          Show detailed information and disk usage
  --json                 Output as JSON
  -h, --help             Show this message and exit

Examples:
  prime-uve list              # List all managed venvs
  prime-uve list --orphan-only  # Show only problems
  prime-uve list --verbose    # Show full details
  prime-uve list --json       # Machine-readable output
```

### README.md Section

```markdown
## List Managed Virtual Environments

See all projects managed by prime-uve:

```bash
prime-uve list
```

Output shows:
- Project name
- Venv location
- Validation status (✓ valid, ✗ orphaned, ⚠ mismatch)

### Filters

Show only orphaned venvs:
```bash
prime-uve list --orphan-only
```

Show detailed information:
```bash
prime-uve list --verbose
```

Get machine-readable JSON:
```bash
prime-uve list --json
```
```

## Success Metrics

- [ ] Accurately lists all cached projects
- [ ] Validation detects all issue types
- [ ] Performance acceptable with 100+ projects
- [ ] Table formatting readable on various terminal sizes
- [ ] JSON output parseable by scripts
- [ ] Empty cache handled gracefully
- [ ] Helpful tips guide users to next actions
- [ ] Test coverage >90%

## Next Task Dependencies

This task enables:
- Task 3.4: `prime-uve prune` - Uses validation logic to identify orphans
- Better user visibility into prime-uve's state

## Estimated Complexity

**Medium** - Straightforward logic with good infrastructure support.

Estimated effort: 3-4 hours including tests and documentation.
