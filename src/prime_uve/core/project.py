"""Project detection and metadata extraction for prime-uve.

This module provides utilities to locate Python project roots (by finding
pyproject.toml) and extract project metadata needed for venv path generation
and display.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .paths import get_project_name


class ProjectError(Exception):
    """Raised when project operations fail."""

    pass


@dataclass
class ProjectMetadata:
    """Project metadata extracted from pyproject.toml and filesystem."""

    name: str  # Project name (from pyproject or dirname)
    path: Path  # Absolute path to project root
    has_pyproject: bool  # True if pyproject.toml exists
    python_version: str | None  # requires-python field, if present
    description: str | None  # Project description, if present

    @property
    def display_name(self) -> str:
        """Human-readable project name for output."""
        return self.name

    @property
    def is_valid_python_project(self) -> bool:
        """True if this appears to be a valid Python project."""
        return self.has_pyproject


def find_project_root(start_path: Path | None = None) -> Path | None:
    """Find project root by locating pyproject.toml.

    Walks up directory tree from start_path until it finds a directory
    containing pyproject.toml. This is considered the project root.

    Args:
        start_path: Starting directory. Defaults to Path.cwd()

    Returns:
        Path to project root (directory containing pyproject.toml),
        or None if no pyproject.toml found

    Example:
        >>> root = find_project_root()
        >>> print(root)
        Path('/home/user/projects/myproject')
        >>> (root / "pyproject.toml").exists()
        True
    """
    current = (start_path or Path.cwd()).resolve()

    # Walk up directory tree
    while True:
        pyproject_path = current / "pyproject.toml"
        if pyproject_path.exists():
            return current

        # Check if we're at filesystem root
        parent = current.parent
        if parent == current:
            # We've reached the root (parent is same as current)
            return None

        current = parent


def is_python_project(path: Path) -> bool:
    """Check if directory is a Python project.

    A directory is considered a Python project if it contains pyproject.toml.

    Args:
        path: Path to directory to check

    Returns:
        True if directory contains pyproject.toml, False otherwise

    Example:
        >>> is_python_project(Path("/home/user/myproject"))
        True
        >>> is_python_project(Path("/home/user/random-dir"))
        False
    """
    try:
        return (path / "pyproject.toml").exists()
    except (OSError, TypeError):
        return False


def get_project_metadata(project_path: Path) -> ProjectMetadata:
    """Extract project metadata from project directory.

    Reads pyproject.toml if present and extracts relevant information.
    Falls back to directory name for missing fields.

    Args:
        project_path: Path to project root directory

    Returns:
        ProjectMetadata with name, description, Python version, etc.

    Raises:
        ProjectError: If project_path is not a valid project

    Example:
        >>> metadata = get_project_metadata(Path("/home/user/myproject"))
        >>> metadata.name
        'myproject'
        >>> metadata.python_version
        '>=3.13'
    """
    # Validate path
    try:
        resolved_path = project_path.resolve()
        if not resolved_path.exists():
            raise ProjectError(f"Project path does not exist: {project_path}")
        if not resolved_path.is_dir():
            raise ProjectError(f"Project path is not a directory: {project_path}")
    except (OSError, RuntimeError) as e:
        raise ProjectError(f"Invalid project path: {project_path}") from e

    # Check if pyproject.toml exists
    pyproject_path = resolved_path / "pyproject.toml"
    has_pyproject = pyproject_path.exists()

    # Initialize metadata with defaults
    name = None
    python_version = None
    description = None

    # Try to extract metadata from pyproject.toml
    if has_pyproject:
        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                project_section = data.get("project", {})

                # Extract name (must be non-empty string)
                name_from_toml = project_section.get("name")
                if (
                    name_from_toml
                    and isinstance(name_from_toml, str)
                    and name_from_toml.strip()
                ):
                    name = name_from_toml.strip()

                # Extract optional fields
                python_version = project_section.get("requires-python")
                description = project_section.get("description")

        except (tomllib.TOMLDecodeError, OSError, KeyError):
            # Malformed or unreadable pyproject.toml - continue with fallback
            pass

    # Fall back to directory name if no valid name found
    if not name:
        name = get_project_name(resolved_path)

    return ProjectMetadata(
        name=name,
        path=resolved_path,
        has_pyproject=has_pyproject,
        python_version=python_version,
        description=description,
    )
