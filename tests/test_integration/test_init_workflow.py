"""Integration tests for init workflow."""

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
        """[project]
name = "integration-test"
version = "0.1.0"
dependencies = []

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
"""
    )

    return project_dir


@pytest.fixture
def cache_file(tmp_path):
    """Create a cache file path."""
    cache_file = tmp_path / ".prime-uve" / "cache.json"
    cache_file.parent.mkdir(exist_ok=True)
    return cache_file


def test_init_then_uve_sync(runner, test_project, cache_file, monkeypatch):
    """Test that uve sync works after init (venv created by uv)."""
    monkeypatch.chdir(test_project)

    with patch("prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file):
        # Run init
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0

        # Read .env.uve to get venv path
        env_file = test_project / ".env.uve"
        assert env_file.exists()

        env_vars = read_env_file(env_file)
        venv_path = env_vars.get("UV_PROJECT_ENVIRONMENT")
        assert venv_path is not None

        # Verify .env.uve is readable and valid
        assert "${HOME}" in venv_path or "$HOME" in venv_path


def test_init_then_list(runner, test_project, cache_file, monkeypatch):
    """Test that init + list shows correct entry."""
    monkeypatch.chdir(test_project)

    with patch("prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file):
        # Run init
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0

        # Verify cache entry exists
        cache = Cache(cache_path=cache_file)
        mappings = cache.list_all()
        assert len(mappings) == 1
        assert str(test_project) in mappings

        # Verify cache entry has correct structure
        entry = mappings[str(test_project)]
        assert "venv_path" in entry
        assert "project_name" in entry
        assert "path_hash" in entry
        assert entry["project_name"] == "integration-test"


def test_init_force_workflow(runner, test_project, cache_file, monkeypatch):
    """Test force reinitialization workflow."""
    monkeypatch.chdir(test_project)

    with patch("prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file):
        # First init
        result1 = runner.invoke(cli, ["init"])
        assert result1.exit_code == 0

        # Read first venv path
        env_vars1 = read_env_file(test_project / ".env.uve")
        venv_path1 = env_vars1["UV_PROJECT_ENVIRONMENT"]

        # Try init without force - should fail
        result2 = runner.invoke(cli, ["init"])
        assert result2.exit_code == 1

        # Force reinit with --yes
        result3 = runner.invoke(cli, ["init", "--force", "--yes"])
        assert result3.exit_code == 0

        # Read second venv path - should be same (same project path)
        env_vars2 = read_env_file(test_project / ".env.uve")
        venv_path2 = env_vars2["UV_PROJECT_ENVIRONMENT"]

        # Paths should be identical since project location didn't change
        assert venv_path1 == venv_path2


def test_init_cross_platform_paths(runner, test_project, cache_file, monkeypatch):
    """Test that paths work correctly on all platforms."""
    monkeypatch.chdir(test_project)

    with patch("prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file):
        result = runner.invoke(cli, ["init"])
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


def test_init_preserves_existing_env_vars(runner, test_project, cache_file, monkeypatch):
    """Test that init preserves existing variables in .env.uve."""
    monkeypatch.chdir(test_project)

    # Create .env.uve with custom variables
    env_file = test_project / ".env.uve"
    env_file.write_text(
        """# My custom variables
DATABASE_URL=postgresql://localhost/mydb
API_KEY=secret123
DEBUG=true
"""
    )

    with patch("prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file):
        # Run init - should preserve existing variables
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0

        # Check that all original variables are preserved
        content = env_file.read_text()
        assert "# My custom variables" in content
        assert "DATABASE_URL=postgresql://localhost/mydb" in content
        assert "API_KEY=secret123" in content
        assert "DEBUG=true" in content
        assert "UV_PROJECT_ENVIRONMENT=" in content

        # Check order preserved (UV_PROJECT_ENVIRONMENT added at end)
        lines = content.splitlines()
        # Last non-empty line should be UV_PROJECT_ENVIRONMENT
        non_empty_lines = [l for l in lines if l.strip()]
        assert non_empty_lines[-1].startswith("UV_PROJECT_ENVIRONMENT=")
