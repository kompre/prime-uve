"""VS Code workspace utilities for venv configuration."""

import json
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


def update_workspace_settings(workspace: dict, interpreter_path: str | Path) -> dict:
    """Update Python settings in workspace data for complete venv integration.

    Applies three settings:
    1. python.defaultInterpreterPath - Points to venv Python interpreter
    2. python.terminal.activateEnvironment - Enables auto-activation in new terminals
    3. python.envFile - Loads environment variables from .env.uve

    Args:
        workspace: Workspace data dict
        interpreter_path: Path to Python interpreter (can include env variables like ${HOME})

    Returns:
        Updated workspace data dict
    """
    if "settings" not in workspace:
        workspace["settings"] = {}

    workspace["settings"]["python.defaultInterpreterPath"] = str(interpreter_path)
    workspace["settings"]["python.terminal.activateEnvironment"] = True
    workspace["settings"]["python.envFile"] = "${workspaceFolder}/.env.uve"

    return workspace


def create_default_workspace(project_root: Path, interpreter_path: str | Path) -> dict:
    """Create workspace structure with complete Python settings.

    Includes all three settings for full venv integration:
    - python.defaultInterpreterPath
    - python.terminal.activateEnvironment
    - python.envFile

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
            "python.terminal.activateEnvironment": True,
            "python.envFile": "${workspaceFolder}/.env.uve",
        },
    }
