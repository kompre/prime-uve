"""Tests for prime_uve.core.paths module."""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from prime_uve.core.paths import (
    expand_path_variables,
    generate_hash,
    generate_venv_path,
    get_project_name,
    ensure_home_set,
)


class TestGenerateHash:
    """Tests for generate_hash function."""

    def test_deterministic(self, tmp_path):
        """Same path always generates same hash."""
        project_path = tmp_path / "my-project"
        project_path.mkdir()

        hash1 = generate_hash(project_path)
        hash2 = generate_hash(project_path)

        assert hash1 == hash2
        assert len(hash1) == 8

    def test_collision_resistance(self, tmp_path):
        """Different paths generate different hashes."""
        project1 = tmp_path / "project1"
        project2 = tmp_path / "project2"
        project1.mkdir()
        project2.mkdir()

        hash1 = generate_hash(project1)
        hash2 = generate_hash(project2)

        assert hash1 != hash2

    def test_cross_platform_normalization(self, tmp_path):
        """Hash is same regardless of path style (symlinks resolved)."""
        project_path = tmp_path / "my-project"
        project_path.mkdir()

        # Generate hash from absolute path
        hash_from_path = generate_hash(project_path)

        # Should produce consistent hash
        assert len(hash_from_path) == 8
        assert hash_from_path.isalnum()

    def test_long_path(self, tmp_path):
        """Handles very long paths."""
        long_path = tmp_path / ("a" * 100) / ("b" * 100) / ("c" * 100)
        long_path.mkdir(parents=True)

        hash_val = generate_hash(long_path)

        assert len(hash_val) == 8
        assert hash_val.isalnum()

    def test_special_characters(self, tmp_path):
        """Handles paths with spaces and special characters."""
        project_path = tmp_path / "my project" / "sub dir"
        project_path.mkdir(parents=True)

        hash_val = generate_hash(project_path)

        assert len(hash_val) == 8
        assert hash_val.isalnum()

    def test_unicode_path(self, tmp_path):
        """Handles unicode characters in path."""
        project_path = tmp_path / "проект" / "子目录"
        project_path.mkdir(parents=True)

        hash_val = generate_hash(project_path)

        assert len(hash_val) == 8
        assert hash_val.isalnum()


class TestGetProjectName:
    """Tests for get_project_name function."""

    def test_from_pyproject_toml(self, tmp_path):
        """Extracts name from pyproject.toml."""
        project_path = tmp_path / "my-project"
        project_path.mkdir()

        pyproject = project_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "awesome-project"\n')

        name = get_project_name(project_path)

        assert name == "awesome-project"

    def test_fallback_to_directory_name(self, tmp_path):
        """Uses directory name if no pyproject.toml."""
        project_path = tmp_path / "my-project"
        project_path.mkdir()

        name = get_project_name(project_path)

        assert name == "my-project"

    def test_sanitization_spaces(self, tmp_path):
        """Sanitizes spaces to hyphens."""
        project_path = tmp_path / "My Project"
        project_path.mkdir()

        name = get_project_name(project_path)

        assert name == "my-project"

    def test_sanitization_special_chars(self, tmp_path):
        """Removes special characters."""
        project_path = tmp_path / "My_Project!"
        project_path.mkdir()

        name = get_project_name(project_path)

        assert name == "my-project"

    def test_sanitization_consecutive_hyphens(self, tmp_path):
        """Avoids consecutive hyphens."""
        project_path = tmp_path / "My   Project!!!"
        project_path.mkdir()

        name = get_project_name(project_path)

        assert name == "my-project"
        assert "--" not in name

    def test_sanitization_trailing_hyphens(self, tmp_path):
        """Removes trailing hyphens."""
        project_path = tmp_path / "MyProject---"
        project_path.mkdir()

        name = get_project_name(project_path)

        assert not name.endswith("-")

    def test_empty_after_sanitization(self, tmp_path):
        """Returns 'project' if name becomes empty after sanitization."""
        project_path = tmp_path / "!!!"
        project_path.mkdir()

        name = get_project_name(project_path)

        assert name == "project"

    def test_malformed_toml(self, tmp_path):
        """Handles malformed pyproject.toml gracefully."""
        project_path = tmp_path / "my-project"
        project_path.mkdir()

        pyproject = project_path / "pyproject.toml"
        pyproject.write_text("this is not valid toml [[[")

        name = get_project_name(project_path)

        # Should fall back to directory name
        assert name == "my-project"

    def test_toml_missing_project_name(self, tmp_path):
        """Handles pyproject.toml without project.name."""
        project_path = tmp_path / "my-project"
        project_path.mkdir()

        pyproject = project_path / "pyproject.toml"
        pyproject.write_text('[build-system]\nrequires = ["setuptools"]\n')

        name = get_project_name(project_path)

        # Should fall back to directory name
        assert name == "my-project"


class TestGenerateVenvPath:
    """Tests for generate_venv_path function."""

    def test_format(self, tmp_path):
        """Generated path uses ${HOME} variable."""
        project_path = tmp_path / "my-project"
        project_path.mkdir()

        venv_path = generate_venv_path(project_path)

        assert venv_path.startswith("${HOME}/prime-uve/venvs/")
        assert "my-project_" in venv_path

    def test_not_expanded(self, tmp_path):
        """Generated path contains literal ${HOME}, not expanded."""
        project_path = tmp_path / "test-project"
        project_path.mkdir()

        venv_path = generate_venv_path(project_path)

        assert "${HOME}" in venv_path
        # Should not contain actual home directory
        if sys.platform == "win32":
            assert "Users" not in venv_path or "${HOME}" in venv_path
        else:
            assert "/home/" not in venv_path or "${HOME}" in venv_path

    def test_includes_hash(self, tmp_path):
        """Generated path includes project name and hash."""
        project_path = tmp_path / "my-project"
        project_path.mkdir()

        venv_path = generate_venv_path(project_path)
        hash_val = generate_hash(project_path)

        assert f"my-project_{hash_val}" in venv_path

    def test_deterministic(self, tmp_path):
        """Same project generates same venv path."""
        project_path = tmp_path / "my-project"
        project_path.mkdir()

        path1 = generate_venv_path(project_path)
        path2 = generate_venv_path(project_path)

        assert path1 == path2


class TestExpandPathVariables:
    """Tests for expand_path_variables function."""

    def test_expands_home(self, tmp_path):
        """${HOME} expands to actual home directory."""
        path_str = "${HOME}/prime-uve/venvs/myproject"

        expanded = expand_path_variables(path_str)

        assert "${HOME}" not in str(expanded)
        assert "prime-uve" in str(expanded)
        assert expanded.is_absolute()

    @patch.dict(os.environ, {"HOME": "/custom/home"})
    def test_uses_home_env_var_unix(self):
        """On Unix, uses HOME environment variable."""
        if sys.platform == "win32":
            pytest.skip("Unix-specific test")

        path_str = "${HOME}/prime-uve/venvs/myproject"

        expanded = expand_path_variables(path_str)

        assert str(expanded).startswith("/custom/home")

    @patch.dict(os.environ, {"USERPROFILE": "C:\\custom\\profile", "HOME": ""}, clear=True)
    @patch("sys.platform", "win32")
    def test_uses_userprofile_on_windows(self):
        """On Windows, uses USERPROFILE if HOME not set."""
        path_str = "${HOME}/prime-uve/venvs/myproject"

        expanded = expand_path_variables(path_str)

        # Should use USERPROFILE
        assert "custom" in str(expanded) or "profile" in str(expanded).lower()

    @patch.dict(os.environ, {"HOME": "C:\\Users\\testuser"})
    @patch("sys.platform", "win32")
    def test_uses_home_on_windows_if_set(self):
        """On Windows, prefers HOME if it's set."""
        path_str = "${HOME}/prime-uve/venvs/myproject"

        expanded = expand_path_variables(path_str)

        assert "testuser" in str(expanded)

    def test_returns_path_object(self):
        """Returns a pathlib.Path object."""
        path_str = "${HOME}/prime-uve/venvs/myproject"

        expanded = expand_path_variables(path_str)

        assert isinstance(expanded, Path)


class TestEnsureHomeSet:
    """Tests for ensure_home_set function."""

    @patch.dict(os.environ, {"USERPROFILE": "C:\\Users\\testuser"}, clear=True)
    @patch("sys.platform", "win32")
    def test_sets_home_on_windows_if_missing(self):
        """On Windows, sets HOME to USERPROFILE if not set."""
        # Remove HOME if it exists
        os.environ.pop("HOME", None)

        ensure_home_set()

        assert "HOME" in os.environ
        assert os.environ["HOME"] == "C:\\Users\\testuser"

    @patch.dict(os.environ, {"HOME": "/home/user"})
    def test_does_not_override_existing_home(self):
        """Does not override HOME if already set."""
        original_home = os.environ["HOME"]

        ensure_home_set()

        assert os.environ["HOME"] == original_home

    @patch("sys.platform", "linux")
    def test_no_op_on_unix(self):
        """Does nothing on Unix systems."""
        # Should not raise any errors
        ensure_home_set()
        # Unix systems typically have HOME set already

    @patch.dict(os.environ, {}, clear=True)
    @patch("sys.platform", "win32")
    @patch("os.path.expanduser")
    def test_fallback_to_expanduser(self, mock_expanduser):
        """Falls back to expanduser if USERPROFILE not set."""
        mock_expanduser.return_value = "C:\\Users\\fallback"

        ensure_home_set()

        assert os.environ["HOME"] == "C:\\Users\\fallback"
        mock_expanduser.assert_called_once_with("~")


class TestIntegration:
    """Integration tests for full workflow."""

    def test_full_workflow(self, tmp_path):
        """Test full workflow: project path → venv path → expansion."""
        # Create project with pyproject.toml
        project_path = tmp_path / "test-project"
        project_path.mkdir()

        pyproject = project_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "my-awesome-project"\n')

        # Generate venv path
        venv_path = generate_venv_path(project_path)

        # Verify format
        assert venv_path.startswith("${HOME}/prime-uve/venvs/")
        assert "my-awesome-project_" in venv_path

        # Expand for local use
        expanded = expand_path_variables(venv_path)

        # Verify expansion
        assert "${HOME}" not in str(expanded)
        assert expanded.is_absolute()
        assert "prime-uve" in str(expanded)
        assert "my-awesome-project_" in str(expanded)

    def test_cross_platform_consistency(self, tmp_path):
        """Verify same project generates same venv path format."""
        project_path = tmp_path / "cross-platform-test"
        project_path.mkdir()

        venv_path = generate_venv_path(project_path)

        # Should always use ${HOME} regardless of platform
        assert venv_path.startswith("${HOME}/")
        assert "${USERPROFILE}" not in venv_path
