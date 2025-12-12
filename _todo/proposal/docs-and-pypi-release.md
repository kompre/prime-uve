# Task Proposal: Documentation Update and Stable PyPI Release

## Objective

Update README.md with accurate documentation and prepare for stable 1.0.0 release on PyPI. Current version 0.2.0rc12 is already published as release candidate - this task focuses on documentation corrections, complete feature documentation, and preparing for stable release.

## Current State Analysis

**Version**: 0.2.0rc12 (already on PyPI)
**Python**: 3.13+ only
**Status**: Release candidate, needs documentation updates before 1.0.0

### Documentation Issues Found

1. **README.md inaccuracies**:
   - Shows `UV_PROJECT_ENVIRONMENT="$HOME/prime-uve/venvs/..."`
   - **Actually uses**: `UV_PROJECT_ENVIRONMENT="${PRIMEUVE_VENVS_PATH}/project_hash"`
   - **Platform-specific defaults**:
     - Linux: `~/.cache/prime-uve/venvs`
     - macOS: `~/Library/Caches/prime-uve/venvs`
     - Windows: `%LOCALAPPDATA%/prime-uve/Cache/venvs`

2. **VS Code integration not documented**:
   - README has commented-out section for `configure vscode`
   - Command fully implemented with extensive options:
     - `--suffix` - Platform-specific workspaces
     - `--merge` - Merge settings from another workspace
     - `--expand` - Absolute paths instead of VS Code variables
     - `--export-as-default` - Set default workspace in .env.uve
   - Platform-generic variable translation working

3. **Missing command documentation**:
   - `shell` - Spawn shell with venv activated
   - `dir` - Open venvs directory in file explorer
   - `register` - Manually register project in cache
   - `activate` - Output activation commands

4. **How `uve` wrapper works needs clarification**:
   - Command: `uv run --env-file .env.uve -- uv [args]`
   - Automatically injects `PRIMEUVE_VENVS_PATH` environment variable
   - Variable expands to platform-specific cache location

5. **Missing**:
   - CHANGELOG.md file
   - Clear architecture/scope section
   - Migration guide from default uv workflow

## Scope and Architecture (For Review)

### What prime-uve IS

A **thin wrapper for uv** that enables external virtual environment management through automatic environment variable injection.

**Core capabilities**:
- `uve` command wraps uv with automatic `.env.uve` loading
- Manages venvs in platform-specific cache locations (not project directories)
- Tracks venv-to-project mappings in local cache
- Configures VS Code workspaces with platform-generic paths
- Provides shell integration (activate, shell spawn)

### What prime-uve IS NOT

- **Not a uv replacement** - Delegates all package management to uv
- **Not a virtual environment creator** - Uses uv to create venvs
- **Not a package manager** - No dependency resolution or package installation
- **Not like poetry/pipenv** - Doesn't manage dependencies, just venv locations
- **Not a Python version manager** - Use uv's Python management or pyenv

### Core Architecture

```
User runs: uve sync
           ↓
uve wrapper finds .env.uve (walks up directory tree)
           ↓
Injects PRIMEUVE_VENVS_PATH=${platform-cache-path}
           ↓
Runs: uv run --env-file .env.uve -- uv sync
           ↓
uv reads UV_PROJECT_ENVIRONMENT=${PRIMEUVE_VENVS_PATH}/project_hash
           ↓
Variable expands to: ~/.cache/prime-uve/venvs/project_hash (Linux)
           ↓
uv uses external venv at expanded path
```

**Key design principles**:
1. **`.env.uve` is single source of truth** for venv configuration
2. **`${PRIMEUVE_VENVS_PATH}` provides portability** across platforms and users
3. **Platform-aware defaults** respect OS conventions automatically
4. **Cache tracks mappings** for validation and orphan detection
5. **Non-invasive** - Works alongside standard uv workflows

### Use Cases

**When to use prime-uve**:
- Project directory on network share (venv should be local for performance)
- Multiple projects share same name (hash ensures uniqueness)
- Want centralized venv management (easy to locate/clean all venvs)
- Need cross-platform dev (${PRIMEUVE_VENVS_PATH} works everywhere)
- Team collaboration with different OSes

**When NOT to use prime-uve**:
- Project venv in project directory is fine (`.venv/`)
- Don't need external venv locations
- Simple single-user projects
- CI/CD environments (usually rebuild venvs anyway)

## README.md Updates Needed

### 1. Fix "Why prime-uve?" Section

**Current** (lines 12-13):
```markdown
For some project venv location is preferable outside the project root...
```

**Should be**:
```markdown
## Why prime-uve?

Some scenarios require virtual environments outside the project directory:

- **Network shares**: Project on network drive, but venv must be local for performance
- **Multiple workspaces**: Same project cloned in different locations needs separate venvs
- **Centralized management**: All venvs in one location for easy cleanup
- **Cross-platform teams**: Same `.env.uve` works on Linux, macOS, and Windows

uv can use external venvs via the `UV_PROJECT_ENVIRONMENT` variable, but requires it to be set for every command. prime-uve automates this with the `uve` wrapper and `${PRIMEUVE_VENVS_PATH}` variable expansion.
```

### 2. Fix Path Configuration Section

**Current** (lines 99-101):
```markdown
UV_PROJECT_ENVIRONMENT="$HOME/prime-uve/venvs/<project_name>_<hash>"
```

**Should be**:
```markdown
## Path Configuration

`.env.uve` uses `${PRIMEUVE_VENVS_PATH}` variable for cross-platform compatibility:

```bash
UV_PROJECT_ENVIRONMENT="${PRIMEUVE_VENVS_PATH}/myproject_abc123"
```

This variable automatically expands to platform-specific cache locations:

| Platform | Default Path |
|----------|-------------|
| Linux | `~/.cache/prime-uve/venvs` |
| macOS | `~/Library/Caches/prime-uve/venvs` |
| Windows | `%LOCALAPPDATA%\prime-uve\Cache\venvs` |

Override with `PRIMEUVE_VENVS_PATH` environment variable if needed.

The path includes:
- **Project name** from `pyproject.toml`
- **Short hash** derived from project path (ensures uniqueness)
```

### 3. Add Complete VS Code Integration Section

**Currently commented out** - needs to be uncommented and expanded:

```markdown
## VS Code Integration

Configure VS Code workspace files with your external venv using platform-generic variables.

### Basic Usage

```bash
cd your-project/
prime-uve configure vscode
```

Updates (or creates) `.code-workspace` file with interpreter path:
- Linux: `${userHome}/.cache/prime-uve/venvs/project_hash/bin/python`
- macOS: `${userHome}/Library/Caches/prime-uve/venvs/project_hash/bin/python`
- Windows: `${env:LOCALAPPDATA}/prime-uve/Cache/venvs/project_hash/Scripts/python.exe`

### Platform-Specific Workspaces

For teams working across different operating systems:

```bash
# On Linux machine
prime-uve configure vscode --suffix
# Creates: myproject.linux.code-workspace

# On macOS machine
prime-uve configure vscode --suffix
# Creates: myproject.macos.code-workspace

# On Windows machine
prime-uve configure vscode --suffix
# Creates: myproject.windows.code-workspace
```

All workspace files can coexist in version control. Team members open the one for their platform.

### Advanced Options

```bash
# Merge settings from another workspace
prime-uve configure vscode --suffix --merge myproject.code-workspace

# Use absolute paths instead of variables (not recommended)
prime-uve configure vscode --expand

# Set default workspace for future merges
prime-uve configure vscode --export-as-default myproject.code-workspace

# Preview changes without applying
prime-uve configure vscode --dry-run

# Suppress output, get JSON result
prime-uve configure vscode --json
```

### Options Reference

| Option | Description |
|--------|-------------|
| `--suffix [VALUE]` | Create platform-specific workspace (auto-detects OS if no value) |
| `--merge [FILE]` | Merge settings from another workspace (requires --suffix) |
| `--expand` | Use absolute paths instead of VS Code variables |
| `--export-as-default [FILE]` | Save workspace as default in `.env.uve` |
| `--workspace PATH` | Specific workspace file to update |
| `--yes` | Skip confirmation prompts |
| `--dry-run` | Preview changes without applying |
| `--json` | Output result as JSON |
```

### 4. Document All Commands

Add complete commands section before "Architecture":

```markdown
## Commands Reference

### Core Workflow

```bash
prime-uve init              # Initialize project with .env.uve
uve sync                    # Sync dependencies (instead of: uv sync)
uve add requests            # Add package (instead of: uv add requests)
uve run python script.py    # Run script (instead of: uv run python script.py)
```

### Venv Management

```bash
prime-uve list              # List all managed venvs with status
prime-uve list --orphan     # Show only orphaned venvs

prime-uve prune --orphan    # Clean orphaned venvs
prime-uve prune --all       # Clean all venvs
prime-uve prune --current   # Clean current project's venv
prime-uve prune <path>      # Clean specific venv by path
```

### Shell Integration

```bash
prime-uve activate          # Output activation commands for current shell
eval "$(prime-uve activate)"  # Activate venv in current shell (bash/zsh)

prime-uve shell             # Spawn new shell with venv activated
prime-uve shell --shell bash  # Force specific shell
```

### VS Code Integration

```bash
prime-uve configure vscode                    # Update/create workspace
prime-uve configure vscode --suffix           # Platform-specific workspace
prime-uve configure vscode --expand           # Use absolute paths
prime-uve configure vscode --dry-run          # Preview changes
```

### Utilities

```bash
prime-uve dir               # Open venvs directory in file explorer
prime-uve register          # Manually register current project in cache
prime-uve --version         # Show version
```
```

### 5. Add Architecture Section

Replace current "Architecture" section:

```markdown
## How It Works

### The `uve` Wrapper

When you run `uve sync`, here's what happens:

1. `uve` searches for `.env.uve` (walks up directory tree)
2. Injects `PRIMEUVE_VENVS_PATH` environment variable with platform-specific cache path
3. Runs: `uv run --env-file .env.uve -- uv sync`
4. uv reads `UV_PROJECT_ENVIRONMENT=${PRIMEUVE_VENVS_PATH}/project_hash`
5. Variable expands to actual path (e.g., `~/.cache/prime-uve/venvs/project_hash`)
6. uv uses the external venv

### Cache Tracking

prime-uve maintains a local cache (`~/.local/share/prime-uve/cache.json` on Linux) that tracks:
- Project path → Venv path mappings
- Last validation timestamp
- Validation status (valid, orphaned, path mismatch)

This enables:
- `prime-uve list` to show project status
- `prime-uve prune --orphan` to clean deleted projects
- Detection of moved/renamed projects

### Platform-Aware Paths

Venv locations follow OS conventions:
- **Linux**: XDG Base Directory Specification (`~/.cache`)
- **macOS**: Apple guidelines (`~/Library/Caches`)
- **Windows**: Windows folder structure (`%LOCALAPPDATA%`)

Override with `PRIMEUVE_VENVS_PATH` environment variable if needed.
```

## CHANGELOG.md Creation

Need to create `CHANGELOG.md` file documenting version history:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Documentation
- Fixed incorrect venv path examples in README
- Added complete VS Code integration documentation
- Documented all commands (shell, dir, register, activate)
- Added architecture and workflow explanation
- Created CHANGELOG.md

## [0.2.0rc12] - 2025-12-XX

### Added
- VS Code workspace configuration with --suffix, --merge, --expand options
- Platform-generic variable translation for VS Code
- Cross-platform test compatibility

### Fixed
- JSON output suppression for --json flag
- Cross-platform path handling in tests

## [0.2.0] - Earlier

### Added
- Core commands: init, list, prune
- Cache-based venv tracking
- Shell integration (activate, shell)
- dir and register utilities

[Unreleased]: https://github.com/kompre/prime-uve/compare/v0.2.0rc12...HEAD
[0.2.0rc12]: https://github.com/kompre/prime-uve/releases/tag/v0.2.0rc12
```

## PyPI Preparation for 1.0.0

### Current pyproject.toml Status

Already has good metadata:
- ✅ Description, keywords, classifiers
- ✅ URLs (homepage, repository, issues)
- ✅ Author/maintainer
- ✅ Dependencies (filelock, click)
- ✅ Scripts (prime-uve, uve)

**Needs update**:
- Version: `0.2.0rc12` → `1.0.0`
- Python version note in README: Currently shows 3.13+ (accurate)

### Pre-Release Checklist

- [ ] All tests passing (440 tests) ✅ Already passing
- [ ] README.md updated with corrections
- [ ] VS Code integration documented
- [ ] All commands documented
- [ ] CHANGELOG.md created
- [ ] Version bumped to 1.0.0 in pyproject.toml
- [ ] Create release branch (`release/v1.0.0`)
- [ ] PR to main with documentation updates
- [ ] Tag release after merge

### Release Process

1. **Create release branch**:
   ```bash
   git checkout -b release/v1.0.0
   ```

2. **Update version**:
   - `pyproject.toml`: `version = "1.0.0"`

3. **Create PR to main** with:
   - Updated README.md
   - New CHANGELOG.md
   - Version bump

4. **After PR merge**:
   ```bash
   git checkout main
   git pull
   git tag v1.0.0
   git push origin v1.0.0
   ```

5. **Build and publish**:
   ```bash
   uv build
   uv publish  # Requires PyPI credentials
   ```

6. **Create GitHub release**:
   - Title: "v1.0.0 - Stable Release"
   - Body: Copy relevant CHANGELOG.md section
   - Attach build artifacts

7. **Verify**:
   ```bash
   uv tool install --force prime-uve
   prime-uve --version  # Should show 1.0.0
   ```

### Post-Release

- Monitor PyPI page for correct README rendering
- Check installation on fresh machines
- Watch for issues/bug reports
- Update documentation site (if created)

## Implementation Plan

### Phase 1: Documentation Updates (2-3 hours)

1. ✅ Fix "Why prime-uve?" section with clear use cases
2. ✅ Correct path configuration section with platform-specific defaults
3. ✅ Add complete VS Code integration documentation
4. ✅ Document all commands with examples
5. ✅ Add "How It Works" architecture section
6. ✅ Create CHANGELOG.md

### Phase 2: Review and Testing (1 hour)

1. Review README renders correctly on GitHub
2. Verify all command examples work
3. Test on fresh machine if possible
4. User review and approval

### Phase 3: Release Preparation (1 hour)

1. Create release branch
2. Bump version to 1.0.0
3. Create PR to main
4. After merge: tag, build, publish
5. Create GitHub release

### Phase 4: Verification (30 minutes)

1. Verify PyPI page renders correctly
2. Test `uv tool install prime-uve`
3. Monitor for issues

## Open Questions

### Documentation Tone and Scope

1. **README completeness**: Is the proposed structure sufficient or too detailed?
2. **Migration guide**: Should we add a section on migrating from standard uv workflow?
3. **Comparison table**: Would a comparison with direnv/poetry/other tools be helpful?
4. **Diagrams**: Should we add visual diagrams of the workflow?

### Release Readiness

1. **Feature completeness**: Are there any planned features that should block 1.0.0?
2. **Known issues**: Any bugs that should be fixed before stable release?
3. **Breaking changes**: Any API changes planned before 1.0.0?
4. **Stability**: Is 0.2.0rc12 stable enough for production use?

### Scope Definition

**Please review the "Scope and Architecture" section above.** Specific feedback needed:
- Accuracy of "What prime-uve IS/IS NOT"
- Completeness of architecture description
- Use cases - are they clear and realistic?
- Positioning relative to other tools

## Success Criteria

- [ ] README.md accurately reflects actual implementation
- [ ] All documented commands are correct and tested
- [ ] VS Code integration fully documented with all options
- [ ] Platform-specific venv paths correctly documented
- [ ] CHANGELOG.md created with version history
- [ ] Version 1.0.0 successfully published to PyPI
- [ ] PyPI page renders documentation correctly
- [ ] `uv tool install prime-uve` works on all platforms
- [ ] New users can understand project in < 5 minutes

## Files to Modify/Create

**To modify**:
- `README.md` - Major updates to multiple sections
- `pyproject.toml` - Version bump 0.2.0rc12 → 1.0.0

**To create**:
- `CHANGELOG.md` - New file with version history

**To verify**:
- All badges in README still work
- Links point to correct locations
- Example commands are accurate

## Timeline Estimate

- Documentation updates: 2-3 hours
- Review and testing: 1 hour
- Release preparation: 1 hour
- Verification: 30 minutes

**Total**: ~5 hours spread over documentation updates and release process

## Dependencies

- Current tests passing (✅ 440 passing)
- PyPI account with publish access
- GitHub repository access for releases
- User approval of documentation updates

---

**Status**: Awaiting user review of scope/architecture section and approval to proceed
