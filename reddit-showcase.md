# prime-uve: External venv management for uv

**GitHub:** https://github.com/kompre/prime-uve
**PyPI:** https://pypi.org/project/prime-uve/

## What My Project Does

`prime-uve` solves a specific problem with [uv](https://github.com/astral-sh/uv): managing virtual environments stored outside project directories.

If you need venvs in a centralized location (e.g., projects on network shares where local venvs perform better), uv requires setting `UV_PROJECT_ENVIRONMENT` for every command. This gets tedious fast.

`prime-uve` provides two things:

1. **`uve` command** - Shorthand that automatically loads `.env.uve` file for every uv command
   ```bash
   uve sync              # vs: uv run --env-file .env.uve -- uv sync
   uve add requests      # vs: uv run --env-file .env.uve -- uv add requests
   ```

2. **`prime-uve` CLI** - Venv lifecycle management
   - `prime-uve init` - Set up external venv path with auto-generated hash
   - `prime-uve list` - Show all managed venvs with validation
   - `prime-uve prune` - Clean orphaned venvs from deleted/moved projects

The `.env.uve` file contains cross-platform paths like:
```bash
UV_PROJECT_ENVIRONMENT="${PRIMEUVE_VENVS_PATH}/myproject_abc123"
```

The `${PRIMEUVE_VENVS_PATH}` variable expands to platform-specific cache locations:
- Linux: `~/.cache/prime-uve/venvs`
- macOS: `~/Library/Caches/prime-uve/venvs`
- Windows: `%LOCALAPPDATA%\prime-uve\Cache\venvs`

File lookup walks up the directory tree, so commands work from any project subdirectory.

## Target Audience

- Developers working with projects on network shares or cloud-synced folders
- Teams standardizing on uv who need centralized venv storage
- Anyone managing multiple Python projects who wants organized venv locations

This is production-ready for its scope (it's a thin wrapper with minimal complexity). Currently at v0.1.2 with core commands implemented.

## Comparison

**vs standard uv**: uv creates venvs in `.venv/` by default. You can set `UV_PROJECT_ENVIRONMENT` manually, but you'd need to export it in your shell or prefix every command. `prime-uve` automates this via `.env.uve` and adds venv lifecycle tools.

**vs Poetry**: Poetry stores venvs in a cache directory by default (`~/.cache/pypoetry/virtualenvs/`). However, if you've already committed to uv's speed and don't want Poetry's dependency resolution approach, you'd need a different solution. `prime-uve` gives uv users Poetry-like external venv behavior.

**vs direnv/dotenv**: You could use `direnv` to auto-load environment variables, but `prime-uve` is uv-specific, lighter weight, and includes venv management commands (list, prune, orphan detection).

**vs manual .env + uv**: Technically you can do `uv run --env-file .env -- uv [cmd]` yourself. `prime-uve` just wraps that pattern and adds project lifecycle management. If you only have one project, you don't need this. If you manage many projects with external venvs, it reduces friction.

---

**Install:**
```bash
uv tool install prime-uve
```

Feedback welcome. MIT licensed.
