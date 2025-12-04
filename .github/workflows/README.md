# GitHub Actions Workflows

This directory contains parametrized CI/CD workflows that can be easily adapted for different repositories.

## Configuration

All workflows read from `.github/workflows/config.env` for project-specific settings. This makes the workflows portable - just copy the workflows and update the config file.

### config.env

Edit `.github/workflows/config.env` to customize for your project:

```bash
# Project identification
PACKAGE_NAME=prime-uve              # Python package name
PYPI_PACKAGE_NAME=prime-uve         # Name on PyPI (usually same as PACKAGE_NAME)

# Python configuration
PYTHON_VERSION_FILE=.python-version  # File containing Python version

# Source paths
SOURCE_PATHS=src/                   # Source code directory
TEST_PATHS=tests/                   # Test directory

# Branch configuration
MAIN_BRANCH=main                    # Production branch
DEV_BRANCH=dev                      # Development branch

# Dependency groups (from pyproject.toml [dependency-groups])
DEV_GROUP=dev

# Feature flags (true/false)
ENABLE_QUARTO=false                 # Install Quarto for docs
ENABLE_LOCALES=false                # Install system locales for i18n tests
ENABLE_DOCSTRING_VALIDATION=false   # Run docstring validation script

# Documentation patterns (regex for detecting docs-only changes)
DOCS_PATTERNS=^docs/|^examples/|\.md$|^_docs/

# Linting configuration
LINT_COMMAND=uv run ruff check
FORMAT_COMMAND=uv run ruff format
```

## Workflows

### test.yml
**Trigger:** Pull requests to main/dev branches

- Detects documentation-only changes and skips tests
- Runs linter (Ruff)
- Runs pytest tests
- Conditionally installs Quarto/locales/validates docstrings based on config flags

### lint-fix.yml
**Trigger:** Pushes to dev/feature branches, PRs to dev

- Auto-fixes linting issues with Ruff
- Commits fixes automatically
- Prevents linting from blocking development

### check-release-version.yml
**Trigger:** PRs labeled 'release' or 'test-release'

Validates version format and enforces rules:
- **main + 'release' label** → Stable version required (1.0.0)
- **dev + 'test-release' label** → Pre-release version required (1.0.0rc1)
- Checks if tag already exists
- Validates semantic versioning format

### release.yml
**Trigger:** Merged PRs labeled 'release' or 'test-release'

Two release modes:
- **Production (main + 'release')**: Publishes to PyPI, creates git tag, creates GitHub Release
- **Test (dev + 'test-release')**: Publishes to TestPyPI only (no tag, no release)

Runs tests before publishing to ensure quality.

## Release Process

### Production Release (to PyPI)

1. Create PR to `main` branch
2. Add `release` label
3. Ensure version in `pyproject.toml` is stable (e.g., `1.0.0`)
4. Merge PR → Automatically publishes to PyPI, creates tag, creates GitHub Release

### Test Release (to TestPyPI)

1. Create PR to `dev` branch
2. Add `test-release` label
3. Ensure version in `pyproject.toml` is pre-release (e.g., `1.0.0rc1`)
4. Merge PR → Automatically publishes to TestPyPI (no tag, no GitHub release)

## PyPI Configuration

These workflows use **Trusted Publishing** (OIDC) for PyPI authentication. No tokens needed!

### Setup for Production PyPI

1. Go to https://pypi.org/manage/account/publishing/
2. Add new publisher:
   - **PyPI Project Name:** `prime-uve` (or your package name)
   - **Owner:** `your-github-username` or org
   - **Repository:** `prime-uve`
   - **Workflow:** `release.yml`
   - **Environment:** (leave blank)

### Setup for TestPyPI

1. Go to https://test.pypi.org/manage/account/publishing/
2. Add new publisher with same settings as above

## Porting to New Repository

1. Copy `.github/workflows/` directory to new repo
2. Edit `.github/workflows/config.env` with new project settings
3. Set up PyPI Trusted Publishing for both PyPI and TestPyPI
4. Done! Workflows are ready to use

## Feature Flags

The config file supports optional features:

- **ENABLE_QUARTO**: Install Quarto for documentation rendering (test.yml, release.yml)
- **ENABLE_LOCALES**: Install system locales for i18n testing (test.yml, release.yml)
- **ENABLE_DOCSTRING_VALIDATION**: Run `scripts/validate_docstrings.py` (test.yml)

Set to `true` to enable, `false` to disable.
