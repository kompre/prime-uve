# Release Process

This document outlines the process for releasing `prime-uve` to PyPI.

## Prerequisites

1. **PyPI Trusted Publishing configured** for both:
   - Production PyPI: https://pypi.org/manage/account/publishing/
   - TestPyPI: https://test.pypi.org/manage/account/publishing/

2. **GitHub labels created**:
   - `release` - For production releases to PyPI
   - `test-release` - For test releases to TestPyPI

## Release Types

### Test Release (TestPyPI)

**Purpose:** Validate the release process without affecting production PyPI

**Process:**
1. Ensure you're on `dev` branch
2. Bump to pre-release version: `uv version 0.1.0rc1`
3. Create feature branch: `git checkout -b test-release/0.1.0rc1`
4. Commit: `git commit -am "chore: bump version to 0.1.0rc1"`
5. Push: `git push -u origin test-release/0.1.0rc1`
6. Create PR to `dev` branch with `test-release` label
7. Wait for checks to pass
8. Merge PR

**Results:**
- ✅ Published to TestPyPI
- ❌ No git tag created
- ❌ No GitHub Release created

**Verify:**
```bash
pip install --index-url https://test.pypi.org/simple/ prime-uve==0.1.0rc1
```

### Production Release (PyPI)

**Purpose:** Official release to production PyPI

**Process:**
1. Ensure all features are tested and merged to `dev`
2. Create PR from `dev` to `main`
3. Bump to stable version on `dev`: `uv version 0.1.0`
4. Push to `dev`
5. Update PR, add `release` label
6. Wait for checks to pass (validates stable version format)
7. Merge PR to `main`

**Results:**
- ✅ Published to PyPI
- ✅ Git tag created (e.g., `v0.1.0`)
- ✅ GitHub Release created

**Verify:**
```bash
pip install prime-uve==0.1.0
```

## Version Numbering

Follow semantic versioning:

**Stable versions** (for `main` + `release` label):
- `1.0.0` - Major release
- `0.1.0` - Minor release
- `0.0.1` - Patch release

**Pre-release versions** (for `dev` + `test-release` label):
- `1.0.0rc1` - Release candidate
- `1.0.0b1` - Beta release
- `1.0.0a1` - Alpha release

## Automated Checks

### check-release-version.yml
Validates version format and enforces rules:
- `main` + `release` → Must be stable version
- `dev` + `test-release` → Must be pre-release version
- Checks if tag already exists
- Validates semantic versioning

### test.yml
Runs on all PRs:
- Linting (Ruff)
- Tests (pytest)
- Skips for docs-only changes

### release.yml
Triggered on merged PRs with labels:
- Runs tests before publishing
- Publishes to PyPI or TestPyPI based on target
- Creates tags and releases for production

## Rollback

If a release has issues:

1. **Don't delete the PyPI release** - PyPI doesn't allow re-uploading same version
2. **Release a patch version** with fixes:
   ```bash
   uv version --bump patch  # 0.1.0 → 0.1.1
   ```
3. **Mark GitHub release as pre-release** if needed
4. **Document issues** in GitHub release notes

## Common Issues

### "Tag already exists"
- Version wasn't bumped
- Fix: Bump version and push again

### "Invalid version format"
- Pre-release version on main branch
- Stable version on dev branch
- Fix: Use correct version format for target branch

### "Tests failed"
- PR has failing tests
- Fix: Fix tests before merging

## Current Status

**Latest Releases:**
- TestPyPI: `0.1.0rc1` (test release)
- PyPI: Not yet published

**Next Steps:**
1. Merge remaining features to `dev`
2. Test `0.1.0rc2` on TestPyPI if needed
3. Create PR `dev` → `main` for first production release
4. Bump to `0.1.0` and add `release` label
5. Merge to trigger production release
