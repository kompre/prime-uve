"""Integration tests for init workflow."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from prime_uve.cli.main import cli
from prime_uve.core.cache import Cache
from prime_uve.core.env_file import read_env_file


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def test_project(tmp_path):
    """Create a real test project."""
    project_dir = tmp_path / "integration_test_project"
    project_dir.mkdir()

    # Create realistic pyproject.toml
    pyproject = project_dir / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "integration-test"
version = "0.1.0"
dependencies = []

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
"""
    )

    return project_dir


def test_init_then_uve_sync(runner, test_project, tmp_path):
    """Test that uve sync works after init (venv created by uv)."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cache_dir = tmp_path / ".prime-uve"
        cache_dir.mkdir(exist_ok=True)

        with patch("prime_uve.core.cache.Cache._get_cache_dir", return_value=cache_dir):
            # Run init
            result = runner.invoke(cli, ["init"], cwd=str(test_project))
            assert result.exit_code == 0

            # Read .env.uve to get venv path
            env_file = test_project / ".env.uve"
            assert env_file.exists()

            env_vars = read_env_file(env_file)
            venv_path = env_vars.get("UV_PROJECT_ENVIRONMENT")
            assert venv_path is not None

            # Note: We can't actually run `uve sync` in tests without uv installed
            # But we can verify the setup is correct

            # Verify .env.uve is readable and valid
            assert "${HOME}" in venv_path or "$HOME" in venv_path


def test_init_then_list(runner, test_project, tmp_path):
    """Test that init + list shows correct entry."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cache_dir = tmp_path / ".prime-uve"
        cache_dir.mkdir(exist_ok=True)

        with patch("prime_uve.core.cache.Cache._get_cache_dir", return_value=cache_dir):
            # Run init
            result = runner.invoke(cli, ["init"], cwd=str(test_project))
            assert result.exit_code == 0

            # Verify cache entry exists
            cache = Cache()
            with patch.object(cache, "_get_cache_dir", return_value=cache_dir):
                mappings = cache.list_all()
                assert len(mappings) == 1
                assert str(test_project) in mappings

                # Verify cache entry has correct structure
                entry = mappings[str(test_project)]
                assert "venv_path" in entry
                assert "project_name" in entry
                assert "path_hash" in entry
                assert entry["project_name"] == "integration-test"


def test_init_force_workflow(runner, test_project, tmp_path):
    """Test force reinitialization workflow."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cache_dir = tmp_path / ".prime-uve"
        cache_dir.mkdir(exist_ok=True)

        with patch("prime_uve.core.cache.Cache._get_cache_dir", return_value=cache_dir):
            # First init
            result1 = runner.invoke(cli, ["init"], cwd=str(test_project))
            assert result1.exit_code == 0

            # Read first venv path
            env_vars1 = read_env_file(test_project / ".env.uve")
            venv_path1 = env_vars1["UV_PROJECT_ENVIRONMENT"]

            # Try init without force - should fail
            result2 = runner.invoke(cli, ["init"], cwd=str(test_project))
            assert result2.exit_code == 1

            # Force reinit with --yes
            result3 = runner.invoke(cli, ["init", "--force", "--yes"], cwd=str(test_project))
            assert result3.exit_code == 0

            # Read second venv path - should be same (same project path)
            env_vars2 = read_env_file(test_project / ".env.uve")
            venv_path2 = env_vars2["UV_PROJECT_ENVIRONMENT"]

            # Paths should be identical since project location didn't change
            assert venv_path1 == venv_path2


def test_init_cross_platform_paths(runner, test_project, tmp_path):
    """Test that paths work correctly on all platforms."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cache_dir = tmp_path / ".prime-uve"
        cache_dir.mkdir(exist_ok=True)

        with patch("prime_uve.core.cache.Cache._get_cache_dir", return_value=cache_dir):
            result = runner.invoke(cli, ["init"], cwd=str(test_project))
            assert result.exit_code == 0

            # Read .env.uve
            env_file = test_project / ".env.uve"
            content = env_file.read_text()

            # Should use ${HOME} for cross-platform compatibility
            assert "${HOME}" in content

            # Should NOT use platform-specific variables
            assert "${USERPROFILE}" not in content
            assert "%USERPROFILE%" not in content

            # Path should be valid (no double slashes, etc.)
            env_vars = read_env_file(env_file)
            venv_path = env_vars["UV_PROJECT_ENVIRONMENT"]

            # Should be properly formatted path
            assert "//" not in venv_path
            assert venv_path.count("${HOME}") == 1
