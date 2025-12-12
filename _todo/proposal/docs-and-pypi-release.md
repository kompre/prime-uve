# Task Proposal: Documentation Update and PyPI Release

## Objective

Prepare comprehensive user-facing documentation and release prime-uve to PyPI for public distribution. This involves updating README.md with clear scope definition, installation instructions, feature showcase, and VS Code integration guide.

## Problem Statement

Current state:
- README.md likely outdated or incomplete
- No clear documentation of project scope and architecture
- Missing installation instructions for end users
- VS Code integration features not documented
- Package not yet published to PyPI for easy installation

Before releasing to PyPI, users need:
- Clear understanding of what prime-uve does and doesn't do
- Simple installation instructions (preferably `uv tool install prime-uve`)
- Quick feature overview to understand capabilities
- Guidance on VS Code workspace integration

## Scope Definition Requirements

The README should clearly define:

### What prime-uve IS
- A thin wrapper around `uv` for managing external virtual environments
- A tool to centralize Python venvs outside project directories
- An automation layer for `.env.uve` file management
- A VS Code workspace configurator for venv integration

### What prime-uve IS NOT
- Not a replacement for `uv` itself
- Not a package manager (delegates to `uv`)
- Not a virtual environment manager like `pyenv` or `conda`
- Not a build tool or dependency resolver

### Core Architecture Principles
- **Single source of truth**: `.env.uve` file contains venv configuration
- **Environment variable expansion**: Uses `${PRIMEUVE_VENVS_PATH}` for portability
- **Platform-aware defaults**: Respects OS conventions (XDG on Linux, Library on macOS, AppData on Windows)
- **Cache-based tracking**: Local cache tracks venv-to-project mappings
- **Non-invasive**: Works alongside existing `uv` workflows

**Note**: The scope section is intentionally detailed here for review/editing before implementation.

## README.md Structure

### 1. Header Section
```markdown
# prime-uve

> Centralized virtual environment management for uv projects

[Brief tagline explaining the project in one sentence]

[![PyPI version](badge)]
[![Python versions](badge)]
[![License](badge)]
```

### 2. Scope and Architecture Section

**Content**:
- What prime-uve does (wrapper for external venvs)
- What it doesn't do (not a uv replacement)
- Core architecture (`.env.uve` as single source of truth)
- Why use external venvs (avoid `.venv/` in project roots)
- Platform-aware caching strategy

**Format**:
- Clear bullet points
- Diagrams if helpful (flow of how `uve` command works)
- Links to related tools (uv, pyenv, etc.) for context

### 3. Installation Section

**Content**:
```markdown
## Installation

### Recommended: uv tool install

```bash
uv tool install prime-uve
```

This installs prime-uve globally and makes both `prime-uve` and `uve` commands available.

### Alternative: pipx

```bash
pipx install prime-uve
```

### From source

```bash
git clone https://github.com/kompre/prime-uve.git
cd prime-uve
uv tool install .
```

### Verify installation

```bash
prime-uve --version
uve --version
```

**Requirements**:
- Python 3.11+
- `uv` installed and available in PATH
```

### 4. Quick Features Showcase

**Content**: Practical examples of main commands

```markdown
## Quick Start

### Initialize a project

```bash
cd my-python-project
prime-uve init
```

This creates `.env.uve` with a centralized venv path:
```
UV_PROJECT_ENVIRONMENT=${PRIMEUVE_VENVS_PATH}/my-project_abc123
```

### Use uve instead of uv

```bash
# Instead of: uv sync
uve sync

# Instead of: uv run pytest
uve run pytest

# Instead of: uv add requests
uve add requests
```

The `uve` command automatically loads `.env.uve` before running `uv`.

### List managed venvs

```bash
prime-uve list
```

### Clean up orphaned venvs

```bash
prime-uve prune --orphan
```

### Activate venv in shell

```bash
eval "$(prime-uve activate)"
```
```

**Format**:
- Show most common workflows
- Include expected output examples
- Keep examples concise and realistic
- Focus on the "happy path"

### 5. VS Code Integration Section

**Content**:

```markdown
## VS Code Integration

prime-uve can configure VS Code workspace files to use your centralized venv.

### Basic usage

```bash
prime-uve configure vscode
```

Updates your `.code-workspace` file with the interpreter path using platform-generic variables:
- Linux: `${userHome}/.cache/prime-uve/venvs/...`
- macOS: `${userHome}/Library/Caches/prime-uve/venvs/...`
- Windows: `${env:LOCALAPPDATA}/prime-uve/Cache/venvs/...`

### Platform-specific workspaces

For multi-platform teams, create separate workspace files per OS:

```bash
# On Linux
prime-uve configure vscode --suffix

# Creates: project.linux.code-workspace
```

```bash
# On macOS
prime-uve configure vscode --suffix

# Creates: project.macos.code-workspace
```

All workspace files can coexist in version control.

### Absolute paths (not recommended)

If you prefer absolute paths over variables:

```bash
prime-uve configure vscode --expand
```

**Note**: This makes the workspace machine-specific.

### Options

- `--suffix [VALUE]` - Create platform-specific workspace (auto-detects OS if no value)
- `--expand` - Use absolute paths instead of VS Code variables
- `--merge [FILE]` - Merge settings from another workspace
- `--export-as-default [FILE]` - Save workspace as default in `.env.uve`
- `--yes` - Skip confirmation prompts
- `--json` - Output result as JSON

### What it configures

Sets the following in your workspace:
```json
{
  "settings": {
    "python.defaultInterpreterPath": "${userHome}/.cache/prime-uve/venvs/project_hash/bin/python",
    "python.terminal.activateEnvironment": true,
    "python.envFile": "${workspaceFolder}/.env.uve"
  }
}
```
```

**Format**:
- Start with simplest usage
- Show advanced options with clear use cases
- Explain multi-platform team workflow
- Include JSON example of what gets configured

### 6. Additional Sections (Brief)

**Commands Reference**:
- Link to full CLI documentation (or inline brief descriptions)
- List all commands with one-line descriptions

**Configuration**:
- Environment variables (`PRIMEUVE_VENVS_PATH`, `PRIMEUVE_DEFAULT_CW`)
- `.env.uve` file format
- Cache location

**Troubleshooting**:
- Common issues and solutions
- How to verify installation
- How to reset/reinit

**Contributing**:
- Link to CONTRIBUTING.md (if exists)
- Brief note on development setup

**License**:
- License type (MIT, Apache, etc.)

## PyPI Release Checklist

### Pre-release validation
- [ ] All tests passing (440+ tests)
- [ ] Version number updated in `pyproject.toml`
- [ ] CHANGELOG.md updated with release notes
- [ ] README.md reviewed and complete
- [ ] License file present
- [ ] Package builds successfully (`uv build`)

### PyPI metadata (in pyproject.toml)
- [ ] Project description
- [ ] Keywords for discoverability
- [ ] Classifiers (Python versions, license, status)
- [ ] Homepage URL
- [ ] Repository URL
- [ ] Documentation URL (if applicable)
- [ ] Author/maintainer info

### Release process
1. Create release branch (`release/v0.x.x`)
2. Update version in `pyproject.toml`
3. Update CHANGELOG.md
4. Create PR to main
5. After merge: Tag release (`git tag v0.x.x`)
6. Build package: `uv build`
7. Test upload to TestPyPI: `uv publish --test`
8. Verify installation from TestPyPI
9. Production upload: `uv publish`
10. Verify installation: `uv tool install prime-uve`
11. Create GitHub release with notes

### Post-release
- [ ] Announcement (if applicable)
- [ ] Update documentation site (if exists)
- [ ] Monitor issue tracker for installation problems

## Open Questions for User

### Scope Section
**Please review and edit the "What prime-uve IS/IS NOT" section above.** This is the most critical part for setting user expectations. Specific questions:

1. **Scope accuracy**: Does the description match your vision?
2. **Architecture principles**: Are the listed principles complete?
3. **Positioning**: How should we position prime-uve relative to other tools (uv, pyenv, poetry, pipenv)?
4. **Key differentiators**: What makes prime-uve unique? (centralized venvs? `.env.uve` convention? VS Code integration?)

### Documentation Tone
- Should the README be tutorial-style or reference-style?
- How technical should it be? (beginner-friendly vs. assumes uv knowledge)
- Should we include comparison tables (prime-uve vs direnv, etc.)?

### PyPI Release
- What should the initial version number be? (0.1.0? 1.0.0?)
- Are we ready for public release or should this be marked as alpha/beta?
- Should we publish to TestPyPI first for validation?

### Feature Completeness
- Are there any features that should be implemented before PyPI release?
- Any known bugs that are blockers?
- Should we wait for more real-world testing?

## Implementation Steps

### Phase 1: Scope Definition (Collaborative)
1. User reviews and edits the "Scope and Architecture" content above
2. Finalize positioning and key messages
3. Approve README structure and sections

### Phase 2: README Writing
1. Write header section with badges
2. Write scope/architecture section (based on approved content)
3. Write installation section with all methods
4. Write quick features showcase with examples
5. Write VS Code integration section
6. Write supporting sections (commands, config, troubleshooting)
7. Add diagrams/visuals if needed

### Phase 3: PyPI Preparation
1. Review/update `pyproject.toml` metadata
2. Create/update CHANGELOG.md
3. Verify all package metadata
4. Test build process
5. Create release branch

### Phase 4: Release
1. Create PR to main with documentation updates
2. After merge: Tag and build
3. Upload to TestPyPI
4. Verify TestPyPI installation
5. Upload to production PyPI
6. Create GitHub release

### Phase 5: Validation
1. Test installation on clean machine
2. Verify README renders correctly on PyPI
3. Monitor for issues

## Files to Create/Modify

**To modify**:
- `README.md` - Complete rewrite/major update
- `pyproject.toml` - Update metadata for PyPI
- `CHANGELOG.md` - Add release notes (create if doesn't exist)

**To verify exist**:
- `LICENSE` - License file
- `.gitignore` - Ensure build artifacts ignored
- `pyproject.toml` - Build system configuration

**To review**:
- Any existing docs in `docs/` directory
- Contributing guidelines
- Code of conduct (if applicable)

## Success Criteria

- [ ] README.md clearly explains what prime-uve is and isn't
- [ ] Installation instructions work on all platforms
- [ ] Quick start guide enables new users to get running in < 5 minutes
- [ ] VS Code integration is well-documented with examples
- [ ] Package successfully installs from PyPI via `uv tool install prime-uve`
- [ ] PyPI page displays README correctly with all badges/links
- [ ] First-time users can understand the project without reading code

## Timeline Estimate

- Scope definition: 1-2 iterations with user feedback
- README writing: 2-3 hours
- PyPI preparation: 1 hour
- Release process: 1 hour
- Validation: 30 minutes

**Total**: ~5-6 hours spread over scope approval and implementation

## Dependencies

- Existing codebase must be stable (tests passing)
- PyPI account credentials available
- GitHub repository configured for releases
- Version number strategy decided

---

**Status**: Awaiting user review of scope section and approval to proceed
