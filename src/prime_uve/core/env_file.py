""".env.uve file management for prime-uve.

This module handles finding, reading, and writing .env.uve files with
variable-aware parsing. Variables like ${HOME} are preserved (not expanded)
during read/write operations for cross-platform compatibility.
"""

from pathlib import Path

from .paths import expand_path_variables


class EnvFileError(Exception):
    """Raised when .env.uve operations fail."""

    pass


def find_env_file(start_path: Path | None = None) -> Path:
    """Find or create .env.uve file using smart lookup logic.

    Search algorithm:
    1. Check current directory for .env.uve
    2. If not found, walk up directory tree to project root (pyproject.toml)
    3. If found project root without .env.uve, create empty one there
    4. If no project root found, create .env.uve in start_path

    Args:
        start_path: Starting directory. Defaults to Path.cwd()

    Returns:
        Path to .env.uve file (always returns a path, creates if needed)

    Example:
        >>> env_file = find_env_file()
        >>> print(env_file)
        /home/user/projects/myproject/.env.uve
    """
    if start_path is None:
        start_path = Path.cwd()
    else:
        start_path = Path(start_path)

    start_path = start_path.resolve()

    # Search for .env.uve starting from current path
    current = start_path
    project_root = None

    # Walk up directory tree to find .env.uve or project root
    while True:
        # Check if .env.uve exists in current directory
        env_file = current / ".env.uve"
        if env_file.exists():
            return env_file

        # Check if this is the project root (has pyproject.toml)
        if (current / "pyproject.toml").exists():
            project_root = current

        # Check if we've reached the filesystem root
        parent = current.parent
        if parent == current:
            # At filesystem root
            break

        current = parent

    # No .env.uve found - create one
    if project_root:
        # Create at project root
        env_file = project_root / ".env.uve"
    else:
        # No project root found, create in start_path
        env_file = start_path / ".env.uve"

    # Create empty file
    try:
        env_file.touch()
    except (OSError, PermissionError) as e:
        raise EnvFileError(f"Cannot create .env.uve at {env_file}: {e}") from e

    return env_file


def find_env_file_strict(start_path: Path | None = None) -> Path:
    """Find .env.uve file without creating it if missing.

    Search algorithm:
    1. Check current directory for .env.uve
    2. If not found, walk up directory tree to project root (pyproject.toml)
    3. If not found at project root, raise EnvFileError

    Args:
        start_path: Starting directory. Defaults to Path.cwd()

    Returns:
        Path to existing .env.uve file

    Raises:
        EnvFileError: If .env.uve is not found

    Example:
        >>> env_file = find_env_file_strict()
        >>> print(env_file)
        /home/user/projects/myproject/.env.uve
    """
    if start_path is None:
        start_path = Path.cwd()
    else:
        start_path = Path(start_path)

    start_path = start_path.resolve()

    # Search for .env.uve starting from current path
    current = start_path
    project_root = None

    # Walk up directory tree to find .env.uve or project root
    while True:
        # Check if .env.uve exists in current directory
        env_file = current / ".env.uve"
        if env_file.exists():
            return env_file

        # Check if this is the project root (has pyproject.toml)
        if (current / "pyproject.toml").exists():
            project_root = current

        # Check if we've reached the filesystem root
        parent = current.parent
        if parent == current:
            # At filesystem root
            break

        current = parent

    # No .env.uve found - raise error
    if project_root:
        raise EnvFileError(
            f".env.uve not found in project at {project_root}\n"
            f"Run 'prime-uve init' to create one, or create it manually."
        )
    else:
        raise EnvFileError(
            f".env.uve not found starting from {start_path}\n"
            f"Run 'prime-uve init' to create one, or create it manually."
        )


def read_env_file(path: Path) -> dict[str, str]:
    """Read .env.uve file and parse variables WITHOUT expanding them.

    Parsing rules:
    - Lines with '=' are key-value pairs
    - Leading/trailing whitespace stripped from keys and values
    - Comments (lines starting with #) ignored
    - Empty lines ignored
    - Variables (${...}) are NOT expanded, kept as-is

    Args:
        path: Path to .env.uve file

    Returns:
        Dict of variable name → value (with variables unexpanded)

    Raises:
        EnvFileError: If file cannot be read or parsed

    Example:
        >>> env = read_env_file(Path(".env.uve"))
        >>> env["UV_PROJECT_ENVIRONMENT"]
        '${HOME}/prime-uve/venvs/myproject_a1b2c3d4'  # NOT expanded
    """
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise EnvFileError(f"File not found: {path}") from e
    except PermissionError as e:
        raise EnvFileError(f"Permission denied: {path}") from e
    except OSError as e:
        raise EnvFileError(f"Cannot read file {path}: {e}") from e

    env_vars = {}

    for line in content.splitlines():
        # Strip whitespace
        line = line.strip()

        # Skip comments and empty lines
        if not line or line.startswith("#"):
            continue

        # Parse key=value
        if "=" not in line:
            # Ignore malformed lines without '='
            continue

        # Split on first '=' to allow '=' in values
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()

        if key:  # Ignore lines with empty key
            env_vars[key] = value

    return env_vars


def write_env_file(path: Path, env_vars: dict[str, str]) -> None:
    """Write environment variables to .env.uve file.

    Variables are written as-is (not expanded). If variables contain
    expandable syntax like ${HOME}, they are preserved.

    Args:
        path: Path to .env.uve file
        env_vars: Dict of variable name → value

    Raises:
        EnvFileError: If file cannot be written

    Example:
        >>> write_env_file(
        ...     Path(".env.uve"),
        ...     {"UV_PROJECT_ENVIRONMENT": "${HOME}/prime-uve/venvs/proj_abc123"}
        ... )
    """
    # Create parent directories if needed
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError) as e:
        raise EnvFileError(f"Cannot create parent directory for {path}: {e}") from e

    # Sort keys for consistent output
    sorted_keys = sorted(env_vars.keys())

    # Build content
    lines = [f"{key}={env_vars[key]}" for key in sorted_keys]
    content = "\n".join(lines)

    # Add trailing newline if there's content
    if content:
        content += "\n"

    # Write file
    try:
        path.write_text(content, encoding="utf-8")
    except PermissionError as e:
        raise EnvFileError(f"Permission denied: {path}") from e
    except OSError as e:
        raise EnvFileError(f"Cannot write file {path}: {e}") from e


def update_env_file(path: Path, updates: dict[str, str]) -> None:
    """Update specific variables in .env.uve file, preserving others.

    Args:
        path: Path to .env.uve file
        updates: Dict of variables to add/update

    Raises:
        EnvFileError: If file cannot be read or written

    Example:
        >>> update_env_file(
        ...     Path(".env.uve"),
        ...     {"UV_PROJECT_ENVIRONMENT": "${HOME}/prime-uve/venvs/proj_new"}
        ... )
    """
    # Read existing variables (or start with empty dict if file doesn't exist)
    if path.exists():
        env_vars = read_env_file(path)
    else:
        env_vars = {}

    # Apply updates
    env_vars.update(updates)

    # Write back
    write_env_file(path, env_vars)


def update_env_file_preserve_format(path: Path, updates: dict[str, str]) -> None:
    """Update specific variables in .env.uve, preserving file format and order.

    This function:
    - Preserves comments and blank lines
    - Preserves line order
    - Updates existing variables in-place
    - Appends new variables at the end

    Args:
        path: Path to .env.uve file
        updates: Dict of variables to add/update

    Raises:
        EnvFileError: If file cannot be read or written

    Example:
        >>> update_env_file_preserve_format(
        ...     Path(".env.uve"),
        ...     {"UV_PROJECT_ENVIRONMENT": "${HOME}/prime-uve/venvs/proj_new"}
        ... )
    """
    # If file doesn't exist, just write the new variables
    if not path.exists():
        write_env_file(path, updates)
        return

    # Read existing content line by line
    try:
        content = path.read_text(encoding="utf-8")
    except (FileNotFoundError, PermissionError, OSError) as e:
        raise EnvFileError(f"Cannot read file {path}: {e}") from e

    lines = content.splitlines()
    updated_keys = set()
    new_lines = []

    # Process existing lines
    for line in lines:
        stripped = line.strip()

        # Preserve comments and empty lines as-is
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue

        # Check if this is a variable assignment
        if "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()

            # If this key is being updated, replace the line
            if key in updates:
                new_lines.append(f"{key}={updates[key]}")
                updated_keys.add(key)
            else:
                # Keep the original line
                new_lines.append(line)
        else:
            # Malformed line, keep as-is
            new_lines.append(line)

    # Append any new variables that weren't in the file
    for key, value in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}")

    # Build final content
    content = "\n".join(new_lines)

    # Add trailing newline if there's content
    if content and not content.endswith("\n"):
        content += "\n"

    # Write file
    try:
        path.write_text(content, encoding="utf-8")
    except (PermissionError, OSError) as e:
        raise EnvFileError(f"Cannot write file {path}: {e}") from e


def get_venv_path(env_vars: dict[str, str], expand: bool = False) -> str | Path:
    """Extract venv path from parsed environment variables.

    Args:
        env_vars: Parsed environment variables from read_env_file()
        expand: If True, expand ${HOME} to actual path. If False, return as-is.

    Returns:
        If expand=False: str with variables (e.g., "${HOME}/...")
        If expand=True: Path with variables expanded (e.g., Path("/home/user/..."))

    Raises:
        EnvFileError: If UV_PROJECT_ENVIRONMENT not found

    Example:
        >>> env = read_env_file(Path(".env.uve"))
        >>> get_venv_path(env, expand=False)
        '${HOME}/prime-uve/venvs/myproject_a1b2c3d4'
        >>> get_venv_path(env, expand=True)
        Path('/home/user/prime-uve/venvs/myproject_a1b2c3d4')
    """
    venv_path = env_vars.get("UV_PROJECT_ENVIRONMENT")

    if venv_path is None:
        raise EnvFileError("UV_PROJECT_ENVIRONMENT not found in environment variables")

    if not venv_path.strip():
        raise EnvFileError("UV_PROJECT_ENVIRONMENT is empty")

    if expand:
        return expand_path_variables(venv_path)
    else:
        return venv_path
