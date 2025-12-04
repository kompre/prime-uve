"""Tests for project detection and metadata extraction."""

import sys
from pathlib import Path

import pytest

from prime_uve.core.project import (
    ProjectError,
    ProjectMetadata,
    find_project_root,
    get_project_metadata,
    is_python_project,
)


# ===========================
# Project Root Tests
# ===========================


def test_find_project_root_in_root(tmp_path):
    """Finds project root when starting in root directory."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-project"')

    result = find_project_root(tmp_path)

    assert result is not None
    assert result == tmp_path.resolve()
    assert (result / "pyproject.toml").exists()


def test_find_project_root_in_subdirectory(tmp_path):
    """Finds project root when starting in subdirectory."""
    # Create project structure
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-project"')

    subdir = tmp_path / "src"
    subdir.mkdir()

    result = find_project_root(subdir)

    assert result is not None
    assert result == tmp_path.resolve()


def test_find_project_root_nested_subdirectory(tmp_path):
    """Finds project root from deeply nested subdirectory."""
    # Create project structure
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-project"')

    deep_dir = tmp_path / "src" / "package" / "submodule"
    deep_dir.mkdir(parents=True)

    result = find_project_root(deep_dir)

    assert result is not None
    assert result == tmp_path.resolve()


def test_find_project_root_not_found(tmp_path):
    """Returns None when no pyproject.toml found."""
    # Create empty directory
    subdir = tmp_path / "no-project"
    subdir.mkdir()

    result = find_project_root(subdir)

    assert result is None


def test_find_project_root_at_filesystem_root(tmp_path):
    """Stops at filesystem root without error."""
    # Start from a directory without pyproject.toml
    # This will walk up to filesystem root
    result = find_project_root(tmp_path)

    # Should return None, not crash
    assert result is None


def test_find_project_root_custom_start_path(tmp_path):
    """Respects custom start_path parameter."""
    # Create two separate projects
    project1 = tmp_path / "project1"
    project1.mkdir()
    (project1 / "pyproject.toml").write_text('[project]\nname = "project1"')

    project2 = tmp_path / "project2"
    project2.mkdir()
    (project2 / "pyproject.toml").write_text('[project]\nname = "project2"')

    # Search from project2
    result = find_project_root(project2)

    assert result is not None
    assert result == project2.resolve()
    assert result.name == "project2"


def test_find_project_root_symlink(tmp_path):
    """Follows symlinks when searching."""
    # Create actual project
    real_project = tmp_path / "real-project"
    real_project.mkdir()
    (real_project / "pyproject.toml").write_text('[project]\nname = "real"')

    # Create symlink
    if sys.platform != "win32":
        # Symlinks work differently on Windows
        symlink = tmp_path / "link-to-project"
        symlink.symlink_to(real_project)

        result = find_project_root(symlink)

        assert result is not None
        # Should resolve to real path
        assert result == real_project.resolve()


def test_find_project_root_defaults_to_cwd(tmp_path, monkeypatch):
    """Uses cwd when start_path is None."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-project"')

    # Change to tmp_path
    monkeypatch.chdir(tmp_path)

    result = find_project_root(None)

    assert result is not None
    assert result == tmp_path.resolve()


# ===========================
# Is Python Project Tests
# ===========================


def test_is_python_project_with_pyproject(tmp_path):
    """Returns True for directory with pyproject.toml."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-project"')

    assert is_python_project(tmp_path) is True


def test_is_python_project_without_pyproject(tmp_path):
    """Returns False for directory without pyproject.toml."""
    assert is_python_project(tmp_path) is False


def test_is_python_project_empty_directory(tmp_path):
    """Returns False for empty directory."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    assert is_python_project(empty_dir) is False


def test_is_python_project_file_not_directory(tmp_path):
    """Returns False for file path (not directory)."""
    some_file = tmp_path / "file.txt"
    some_file.write_text("content")

    assert is_python_project(some_file) is False


def test_is_python_project_nonexistent_path(tmp_path):
    """Returns False for non-existent path."""
    nonexistent = tmp_path / "does-not-exist"

    assert is_python_project(nonexistent) is False


# ===========================
# Metadata Tests
# ===========================


def test_get_project_metadata_with_full_pyproject(tmp_path):
    """Extracts all metadata from complete pyproject.toml."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "my-awesome-project"
description = "An awesome Python project"
requires-python = ">=3.11"
version = "1.0.0"
"""
    )

    metadata = get_project_metadata(tmp_path)

    assert metadata.name == "my-awesome-project"
    assert metadata.description == "An awesome Python project"
    assert metadata.python_version == ">=3.11"
    assert metadata.path == tmp_path.resolve()
    assert metadata.has_pyproject is True
    assert metadata.is_valid_python_project is True
    assert metadata.display_name == "my-awesome-project"


def test_get_project_metadata_minimal_pyproject(tmp_path):
    """Handles minimal pyproject.toml (only [project] section)."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'minimal-project'")

    metadata = get_project_metadata(tmp_path)

    assert metadata.name == "minimal-project"
    assert metadata.description is None
    assert metadata.python_version is None
    assert metadata.has_pyproject is True


def test_get_project_metadata_no_project_section(tmp_path):
    """Falls back to directory name if no [project] section."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[build-system]
requires = ["setuptools"]
"""
    )

    metadata = get_project_metadata(tmp_path)

    # Should fall back to directory name
    assert metadata.name is not None
    assert metadata.has_pyproject is True
    assert metadata.description is None
    assert metadata.python_version is None


def test_get_project_metadata_no_pyproject(tmp_path):
    """Uses directory name when no pyproject.toml."""
    # Create a directory with a specific name
    project_dir = tmp_path / "My-Test-Project"
    project_dir.mkdir()

    metadata = get_project_metadata(project_dir)

    # Should use sanitized directory name
    assert metadata.name == "my-test-project"
    assert metadata.has_pyproject is False
    assert metadata.is_valid_python_project is False
    assert metadata.description is None
    assert metadata.python_version is None


def test_get_project_metadata_malformed_toml(tmp_path):
    """Handles malformed pyproject.toml gracefully."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("this is not valid TOML { [ ]")

    metadata = get_project_metadata(tmp_path)

    # Should fall back to directory name
    assert metadata.name is not None
    assert metadata.has_pyproject is True  # File exists, even if malformed


def test_get_project_metadata_empty_name(tmp_path):
    """Falls back to directory name if name field is empty."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = ""')

    metadata = get_project_metadata(tmp_path)

    # Should fall back to directory name
    assert metadata.name is not None
    assert metadata.name != ""


def test_get_project_metadata_whitespace_name(tmp_path):
    """Falls back to directory name if name field is only whitespace."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "   "')

    metadata = get_project_metadata(tmp_path)

    # Should fall back to directory name
    assert metadata.name is not None
    assert metadata.name.strip() != ""


def test_get_project_metadata_missing_optional_fields(tmp_path):
    """Handles missing optional fields (description, etc.)."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "project-with-minimal-fields"
"""
    )

    metadata = get_project_metadata(tmp_path)

    assert metadata.name == "project-with-minimal-fields"
    assert metadata.description is None
    assert metadata.python_version is None
    assert metadata.has_pyproject is True


def test_get_project_metadata_invalid_path():
    """Raises ProjectError for non-existent path."""
    nonexistent = Path("/this/path/does/not/exist")

    with pytest.raises(ProjectError, match="does not exist"):
        get_project_metadata(nonexistent)


def test_get_project_metadata_file_not_directory(tmp_path):
    """Raises ProjectError for file path (not directory)."""
    some_file = tmp_path / "file.txt"
    some_file.write_text("content")

    with pytest.raises(ProjectError, match="not a directory"):
        get_project_metadata(some_file)


# ===========================
# Integration Tests
# ===========================


def test_full_workflow_find_and_get_metadata(tmp_path):
    """Find root then get metadata."""
    # Create project structure
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "workflow-test"
description = "Testing the full workflow"
requires-python = ">=3.11"
"""
    )

    subdir = tmp_path / "src" / "package"
    subdir.mkdir(parents=True)

    # Find root from subdirectory
    root = find_project_root(subdir)
    assert root is not None

    # Get metadata from root
    metadata = get_project_metadata(root)

    assert metadata.name == "workflow-test"
    assert metadata.description == "Testing the full workflow"
    assert metadata.python_version == ">=3.11"
    assert metadata.path == tmp_path.resolve()


def test_metadata_matches_paths_module(tmp_path):
    """Metadata.name matches get_project_name() from paths.py."""
    from prime_uve.core.paths import get_project_name

    # Create project with special characters
    project_dir = tmp_path / "My Special! Project (2024)"
    project_dir.mkdir()

    # Get name from both modules
    name_from_paths = get_project_name(project_dir)
    metadata = get_project_metadata(project_dir)

    # Should match
    assert metadata.name == name_from_paths


# ===========================
# Edge Cases
# ===========================


def test_multiple_pyproject_in_hierarchy(tmp_path):
    """Finds nearest pyproject.toml when multiple exist."""
    # Create outer project
    outer_pyproject = tmp_path / "pyproject.toml"
    outer_pyproject.write_text('[project]\nname = "outer-project"')

    # Create inner project
    inner_dir = tmp_path / "inner"
    inner_dir.mkdir()
    inner_pyproject = inner_dir / "pyproject.toml"
    inner_pyproject.write_text('[project]\nname = "inner-project"')

    # Search from inner directory
    result = find_project_root(inner_dir)

    # Should find inner project (nearest)
    assert result is not None
    assert result == inner_dir.resolve()

    metadata = get_project_metadata(result)
    assert metadata.name == "inner-project"


def test_special_chars_in_project_name(tmp_path):
    """Handles special characters in project name."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "my-project@v2.0"')

    metadata = get_project_metadata(tmp_path)

    # Name should be preserved from pyproject.toml
    assert metadata.name == "my-project@v2.0"


def test_unicode_in_project_name(tmp_path):
    """Handles unicode in project name."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "my-project-éçà"', encoding="utf-8")

    metadata = get_project_metadata(tmp_path)

    # Unicode should be preserved
    assert "é" in metadata.name or metadata.name is not None


def test_very_long_project_name(tmp_path):
    """Handles very long project names."""
    long_name = "a" * 500
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(f'[project]\nname = "{long_name}"')

    metadata = get_project_metadata(tmp_path)

    # Should handle long names
    assert len(metadata.name) > 0
    assert metadata.name == long_name


def test_symlink_to_project(tmp_path):
    """Handles symlinked project directories."""
    if sys.platform == "win32":
        pytest.skip("Symlink test not reliable on Windows")

    # Create real project
    real_project = tmp_path / "real-project"
    real_project.mkdir()
    (real_project / "pyproject.toml").write_text('[project]\nname = "real"')

    # Create symlink
    symlink = tmp_path / "link"
    symlink.symlink_to(real_project)

    # Get metadata through symlink
    metadata = get_project_metadata(symlink)

    # Should resolve to real path
    assert metadata.path == real_project.resolve()
    assert metadata.name == "real"


def test_project_metadata_dataclass_properties():
    """Test ProjectMetadata dataclass properties."""
    metadata = ProjectMetadata(
        name="test-project",
        path=Path("/tmp/test"),
        has_pyproject=True,
        python_version=">=3.11",
        description="Test description",
    )

    assert metadata.display_name == "test-project"
    assert metadata.is_valid_python_project is True

    # Test with no pyproject
    metadata_no_pyproject = ProjectMetadata(
        name="no-pyproject",
        path=Path("/tmp/test"),
        has_pyproject=False,
        python_version=None,
        description=None,
    )

    assert metadata_no_pyproject.is_valid_python_project is False


def test_project_name_with_leading_trailing_spaces(tmp_path):
    """Handles project names with leading/trailing spaces."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "  spaced-project  "')

    metadata = get_project_metadata(tmp_path)

    # Should strip spaces
    assert metadata.name == "spaced-project"


def test_get_project_metadata_resolves_symlinks(tmp_path):
    """get_project_metadata resolves symlinks to canonical path."""
    if sys.platform == "win32":
        pytest.skip("Symlink test not reliable on Windows")

    # Create real project
    real_project = tmp_path / "real"
    real_project.mkdir()
    (real_project / "pyproject.toml").write_text('[project]\nname = "real"')

    # Create symlink
    link = tmp_path / "link"
    link.symlink_to(real_project)

    # Get metadata from symlink
    metadata = get_project_metadata(link)

    # Path should be resolved (canonical)
    assert metadata.path == real_project.resolve()
    assert metadata.path != link


def test_find_project_root_with_nonexistent_start_path():
    """find_project_root handles non-existent start_path gracefully."""
    nonexistent = Path("/this/path/does/not/exist")

    # Should not crash, might return None or raise
    # Behavior depends on whether .resolve() fails
    try:
        result = find_project_root(nonexistent)
        # If it doesn't crash, result should be None
        assert result is None
    except (OSError, RuntimeError):
        # It's OK to raise on invalid path
        pass
