# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Documentation
- Fixed incorrect venv path examples in README (now shows `${PRIMEUVE_VENVS_PATH}`)
- Added complete VS Code integration documentation with all options
- Documented all commands: shell, dir, register, activate
- Added "How It Works" architecture section explaining uve and prime-uve
- Clarified platform-specific default venv locations
- Created CHANGELOG.md

## [0.2.0rc12] - 2025-12-11

### Added
- VS Code workspace configuration with --suffix, --merge, --expand, --export-as-default options
- Platform-generic variable translation for VS Code (`${userHome}`, `${env:LOCALAPPDATA}`)
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
- `uve` wrapper command for automatic `.env.uve` loading

[Unreleased]: https://github.com/kompre/prime-uve/compare/v0.2.0rc12...HEAD
[0.2.0rc12]: https://github.com/kompre/prime-uve/releases/tag/v0.2.0rc12
