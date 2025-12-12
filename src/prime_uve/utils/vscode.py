"""VS Code workspace utilities for venv configuration."""

import json
import os
import platform
from pathlib import Path


def find_workspace_files(project_root: Path) -> list[Path]:
    """Find all .code-workspace files in project.

    Searches in:
    1. Project root
    2. .vscode directory

    Args:
        project_root: Path to project root

    Returns:
        Sorted list of workspace file paths
    """
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


def find_default_workspace(
    project_root: Path, workspace_files: list[Path]
) -> Path | None:
    """Find the default workspace file to use for merging.

    Priority order:
    1. Workspace files without platform suffixes (not ending in .linux, .macos, .windows, etc.)
    2. Among those, prefer one matching the project name
    3. If multiple remain, take alphabetically first
    4. If all have platform suffixes, take alphabetically first

    Args:
        project_root: Path to project root
        workspace_files: List of available workspace files

    Returns:
        Path to default workspace file, or None if no files exist
    """
    if not workspace_files:
        return None

    PLATFORM_SUFFIXES = ["linux", "macos", "windows", "darwin", "win32"]

    # Filter out files with platform suffixes
    non_platform_files = []
    for wf in workspace_files:
        # Get the stem and check if it ends with a platform suffix
        stem = wf.stem  # e.g., "project.linux" -> "project.linux"
        parts = stem.split(".")
        if len(parts) > 1 and parts[-1] in PLATFORM_SUFFIXES:
            continue  # Skip platform-suffixed files
        non_platform_files.append(wf)

    # If we have non-platform files, prefer those
    candidates = non_platform_files if non_platform_files else workspace_files

    # Among candidates, prefer one matching project name
    project_name = project_root.name
    preferred_name = f"{project_name}.code-workspace"
    for candidate in candidates:
        if candidate.name == preferred_name:
            return candidate

    # Otherwise, return alphabetically first
    return sorted(candidates)[0]


def strip_json_comments(content: str) -> str:
    """Remove // and /* */ comments from JSON string.

    VS Code workspace files may contain comments which are not valid in
    standard JSON. This removes them before parsing.

    Args:
        content: JSON string potentially containing comments

    Returns:
        JSON string with comments removed
    """
    # Process character by character to track string context
    result = []
    i = 0
    in_string = False
    escape_next = False

    while i < len(content):
        char = content[i]

        # Handle escape sequences
        if escape_next:
            result.append(char)
            escape_next = False
            i += 1
            continue

        if char == "\\" and in_string:
            result.append(char)
            escape_next = True
            i += 1
            continue

        # Handle string delimiters
        if char == '"':
            in_string = not in_string
            result.append(char)
            i += 1
            continue

        # Only process comments outside strings
        if not in_string:
            # Check for // comment
            if i < len(content) - 1 and content[i : i + 2] == "//":
                # Skip until end of line
                while i < len(content) and content[i] != "\n":
                    i += 1
                continue

            # Check for /* comment
            if i < len(content) - 1 and content[i : i + 2] == "/*":
                # Skip until */
                i += 2
                while i < len(content) - 1:
                    if content[i : i + 2] == "*/":
                        i += 2
                        break
                    i += 1
                continue

        # Regular character
        result.append(char)
        i += 1

    return "".join(result)


def read_workspace(path: Path) -> dict:
    """Read and parse workspace JSON file.

    Handles JSON with comments (VS Code style).

    Args:
        path: Path to .code-workspace file

    Returns:
        Parsed workspace data as dict

    Raises:
        ValueError: If JSON is malformed
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            # Strip comments before parsing
            content = strip_json_comments(content)
            return json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed workspace file: {e}")


def write_workspace(path: Path, data: dict) -> None:
    """Write workspace JSON file with proper formatting.

    Args:
        path: Path to .code-workspace file
        data: Workspace data to write
    """
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")  # Trailing newline


def deep_merge_dicts(base: dict, overlay: dict) -> dict:
    """Deep merge two dictionaries, with overlay taking precedence.

    Args:
        base: Base dictionary
        overlay: Dictionary to merge on top (takes precedence)

    Returns:
        Merged dictionary
    """
    result = base.copy()

    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dicts
            result[key] = deep_merge_dicts(result[key], value)
        else:
            # Overlay value takes precedence
            result[key] = value

    return result


def update_workspace_settings(workspace: dict, interpreter_path: str | Path) -> dict:
    """Update Python settings in workspace data for complete venv integration.

    Applies three settings:
    - python.defaultInterpreterPath - Points to venv Python interpreter

    Args:
        workspace: Workspace data dict
        interpreter_path: Path to Python interpreter (can include env variables like ${env:HOME})

    Returns:
        Updated workspace data dict
    """
    if "settings" not in workspace:
        workspace["settings"] = {}

    workspace["settings"]["python.defaultInterpreterPath"] = str(interpreter_path)

    return workspace


def create_default_workspace(project_root: Path, interpreter_path: str | Path) -> dict:
    """Create workspace structure with complete Python settings.

    Set the default interpreter path based on OS for full venv integration:
    - python.defaultInterpreterPath

    Args:
        project_root: Path to project root
        interpreter_path: Path to Python interpreter (can include env variables like ${HOME})

    Returns:
        New workspace data dict
    """
    return {
        "folders": [{"path": "."}],
        "settings": {
            "python.defaultInterpreterPath": str(interpreter_path),
        },
    }


def get_platform_suffix() -> str:
    """Get user-friendly platform name for workspace suffix.

    Maps Python's platform.system() to user-friendly names:
    - Linux → linux
    - Darwin → macos
    - Windows → windows

    Returns:
        User-friendly platform name (lowercase)
    """
    PLATFORM_SUFFIX_MAP = {
        "Linux": "linux",
        "Darwin": "macos",
        "Windows": "windows",
    }

    return PLATFORM_SUFFIX_MAP.get(platform.system(), platform.system().lower())


def absolute_to_vscode_path(absolute_path: Path) -> str:
    """Convert absolute path to VS Code variable syntax.

    Translates platform-specific paths to VS Code's variable format:
    - Linux: /home/user → ${userHome}
    - macOS: /Users/user → ${userHome}
    - Windows: C:/Users/user/AppData/Local → ${env:LOCALAPPDATA}

    If path cannot be converted to variables (e.g., custom location),
    falls back to absolute path with forward slashes.

    Args:
        absolute_path: Absolute path to convert

    Returns:
        Path with VS Code variables (or absolute path as fallback)
    """
    path_str = str(absolute_path)
    system = platform.system()

    # Convert to forward slashes for consistency
    path_str = path_str.replace("\\", "/")

    if system == "Linux":
        # Try to replace home directory
        home = os.path.expanduser("~").replace("\\", "/")
        if path_str.startswith(home):
            return path_str.replace(home, "${userHome}", 1)

        # Check for XDG_CACHE_HOME
        xdg_cache = os.environ.get("XDG_CACHE_HOME")
        if xdg_cache:
            xdg_cache = xdg_cache.replace("\\", "/")
            if path_str.startswith(xdg_cache):
                return path_str.replace(xdg_cache, "${env:XDG_CACHE_HOME}", 1)

    elif system == "Darwin":  # macOS
        # Replace home directory
        home = os.path.expanduser("~").replace("\\", "/")
        if path_str.startswith(home):
            return path_str.replace(home, "${userHome}", 1)

    elif system == "Windows":
        # Try LOCALAPPDATA first
        localappdata = os.environ.get("LOCALAPPDATA")
        if localappdata:
            localappdata = localappdata.replace("\\", "/")
            if path_str.startswith(localappdata):
                return path_str.replace(localappdata, "${env:LOCALAPPDATA}", 1)

        # Fallback to USERPROFILE
        userprofile = os.environ.get("USERPROFILE")
        if userprofile:
            userprofile = userprofile.replace("\\", "/")
            if path_str.startswith(userprofile):
                return path_str.replace(userprofile, "${userHome}", 1)

    # Fallback: return absolute path with forward slashes
    return path_str


def get_workspace_filename(
    project_root: Path,
    suffix: str | None = None,
    existing_workspace: Path | None = None,
) -> Path:
    """Generate workspace filename with optional suffix.

    Args:
        project_root: Project root directory
        suffix: Optional suffix to insert before .code-workspace
        existing_workspace: Existing workspace file to base name on

    Returns:
        Path to workspace file

    Examples:
        >>> get_workspace_filename(Path('/proj'), None)
        Path('/proj/proj.code-workspace')

        >>> get_workspace_filename(Path('/proj'), 'linux')
        Path('/proj/proj.linux.code-workspace')

        >>> get_workspace_filename(Path('/proj'), 'dev', Path('/proj/foo.code-workspace'))
        Path('/proj/foo.dev.code-workspace')
    """
    if existing_workspace:
        # Extract base name without suffix
        name = existing_workspace.stem
        # Remove existing platform suffixes if any
        for platform_suffix in ["linux", "macos", "windows", "darwin", "win32"]:
            if name.endswith(f".{platform_suffix}"):
                name = name[: -len(platform_suffix) - 1]
                break
    else:
        # Use project name
        name = project_root.name

    # Build filename
    if suffix:
        filename = f"{name}.{suffix}.code-workspace"
    else:
        filename = f"{name}.code-workspace"

    return project_root / filename


def escape_env_variables(path: str) -> str:
    """Escape VS Code environment variable syntax in a given path.
    vscode can access env variable using ${env:VAR_NAME}.

    Args:
        path: The path to escape.

    Returns:
        The escaped path.
    """
    import re

    return re.sub(r"\$\{([^}]+)\}", r"${env:\1}", path)
