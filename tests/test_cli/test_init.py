"""Tests for prime-uve init command."""

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from prime_uve.cli.main import cli
from prime_uve.core.cache import Cache


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_project(tmp_path):
    """Create a mock Python project."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create pyproject.toml
    pyproject = project_dir / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-project"\nversion = "0.1.0"\n')

    return project_dir


@pytest.fixture
def cache_file(tmp_path):
    """Create a cache file path."""
    cache_file = tmp_path / ".prime-uve" / "cache.json"
    cache_file.parent.mkdir(exist_ok=True)
    return cache_file


# Basic Functionality Tests


def test_init_creates_env_file(runner, mock_project, cache_file, monkeypatch):
    """Test that init creates .env.uve with correct content."""
    monkeypatch.chdir(mock_project)

    with patch(
        "prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file
    ):
        result = runner.invoke(cli, ["init"])

        assert result.exit_code == 0, f"Failed with: {result.output}"

        env_file = mock_project / ".env.uve"
        assert env_file.exists()

        content = env_file.read_text()
        assert "UV_PROJECT_ENVIRONMENT=" in content
        assert "${HOME}/.prime-uve/venvs/" in content
        assert "test-project" in content or "test_project" in content


def test_init_adds_to_cache(runner, mock_project, cache_file, monkeypatch):
    """Test that init adds mapping to cache."""
    monkeypatch.chdir(mock_project)

    with patch(
        "prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file
    ):
        result = runner.invoke(cli, ["init"])

        assert result.exit_code == 0

        # Check cache
        cache = Cache(cache_path=cache_file)
        mappings = cache.list_all()
        assert str(mock_project) in mappings


def test_init_uses_variable_form_in_env_file(
    runner, mock_project, cache_file, monkeypatch
):
    """Test that .env.uve contains ${HOME} not expanded path."""
    monkeypatch.chdir(mock_project)

    with patch(
        "prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file
    ):
        result = runner.invoke(cli, ["init"])

        assert result.exit_code == 0

        env_file = mock_project / ".env.uve"
        content = env_file.read_text()

        # Should contain ${HOME}, not expanded path
        assert "${HOME}" in content
        # Should NOT contain actual home directory path
        import os

        home = os.path.expanduser("~")
        assert home not in content


def test_init_success_message_shows_next_steps(
    runner, mock_project, cache_file, monkeypatch
):
    """Test that success output guides user."""
    monkeypatch.chdir(mock_project)

    with patch(
        "prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file
    ):
        result = runner.invoke(cli, ["init"])

        assert result.exit_code == 0

        output = result.output
        assert "Next steps:" in output
        assert "uve sync" in output
        assert "Created .env.uve" in output
        assert "Expanded:" in output


# Already Initialized Tests


def test_init_refuses_overwrite_without_force(
    runner, mock_project, cache_file, monkeypatch
):
    """Test that init refuses to overwrite when UV_PROJECT_ENVIRONMENT is set."""
    monkeypatch.chdir(mock_project)

    with patch(
        "prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file
    ):
        # First init
        result1 = runner.invoke(cli, ["init"])
        assert result1.exit_code == 0

        # Second init without --force should fail (UV_PROJECT_ENVIRONMENT is set)
        result2 = runner.invoke(cli, ["init"])
        assert result2.exit_code == 1
        assert "already initialized" in result2.output.lower()
        assert "UV_PROJECT_ENVIRONMENT" in result2.output


def test_init_allows_init_when_env_file_exists_without_uv_var(
    runner, mock_project, cache_file, monkeypatch
):
    """Test that init works when .env.uve exists but UV_PROJECT_ENVIRONMENT is not set."""
    monkeypatch.chdir(mock_project)

    # Create .env.uve with other variables but no UV_PROJECT_ENVIRONMENT
    env_file = mock_project / ".env.uve"
    env_file.write_text("DATABASE_URL=postgres://localhost\nAPI_KEY=secret\n")

    with patch(
        "prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file
    ):
        result = runner.invoke(cli, ["init"])

        # Should succeed
        assert result.exit_code == 0

        # Should preserve existing variables
        content = env_file.read_text()
        assert "DATABASE_URL=postgres://localhost" in content
        assert "API_KEY=secret" in content
        assert "UV_PROJECT_ENVIRONMENT=" in content


def test_init_force_overwrites(runner, mock_project, cache_file, monkeypatch):
    """Test that init --force overwrites existing setup."""
    monkeypatch.chdir(mock_project)

    with patch(
        "prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file
    ):
        # First init
        runner.invoke(cli, ["init"])

        # Second init with --force and --yes should succeed
        result = runner.invoke(cli, ["init", "--force", "--yes"])
        assert result.exit_code == 0
        assert "Created .env.uve" in result.output or "Added to cache" in result.output


def test_init_force_preserves_other_vars(runner, mock_project, cache_file, monkeypatch):
    """Test that --force preserves other env vars in .env.uve."""
    monkeypatch.chdir(mock_project)

    with patch(
        "prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file
    ):
        # First init
        runner.invoke(cli, ["init"])

        # Add another variable to .env.uve
        env_file = mock_project / ".env.uve"
        content = env_file.read_text()
        content += "CUSTOM_VAR=test_value\n"
        env_file.write_text(content)

        # Force reinit
        runner.invoke(cli, ["init", "--force", "--yes"])

        # Check that custom var is preserved
        new_content = env_file.read_text()
        assert "CUSTOM_VAR=test_value" in new_content
        assert "UV_PROJECT_ENVIRONMENT=" in new_content


def test_init_force_preserves_format(runner, mock_project, cache_file, monkeypatch):
    """Test that --force preserves file format and order."""
    monkeypatch.chdir(mock_project)

    with patch(
        "prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file
    ):
        # First init
        runner.invoke(cli, ["init"])

        # Create a formatted .env.uve with comments
        env_file = mock_project / ".env.uve"
        env_file.write_text(
            """# Database config
DATABASE_URL=postgres://localhost
UV_PROJECT_ENVIRONMENT=${HOME}/.prime-uve/venvs/test_old

# API keys
API_KEY=secret
"""
        )

        # Force reinit
        runner.invoke(cli, ["init", "--force", "--yes"])

        # Check format preserved
        lines = env_file.read_text().splitlines()
        assert lines[0] == "# Database config"
        assert lines[1] == "DATABASE_URL=postgres://localhost"
        # UV_PROJECT_ENVIRONMENT should be updated in place
        assert "UV_PROJECT_ENVIRONMENT=" in lines[2]
        # Comment preserved
        assert "# API keys" in lines
        assert "API_KEY=secret" in lines


def test_init_force_shows_confirmation(runner, mock_project, cache_file, monkeypatch):
    """Test that --force prompts for confirmation without --yes when venv path changes."""
    monkeypatch.chdir(mock_project)

    with patch(
        "prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file
    ):
        # First init
        runner.invoke(cli, ["init"])

        # Manually change the venv path in .env.uve to create a different path
        env_file = mock_project / ".env.uve"
        env_file.write_text(
            "UV_PROJECT_ENVIRONMENT=${HOME}/.prime-uve/venvs/old_venv_path\n"
        )

        # Force without --yes should prompt (we'll cancel it)
        result = runner.invoke(cli, ["init", "--force"], input="n\n")
        assert result.exit_code == 1  # Aborted
        assert "Warning" in result.output or "continue" in result.output.lower()


# Options and Flags Tests


def test_init_dry_run(runner, mock_project, cache_file, monkeypatch):
    """Test that --dry-run shows plan without executing."""
    monkeypatch.chdir(mock_project)

    with patch(
        "prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file
    ):
        result = runner.invoke(cli, ["init", "--dry-run"])

        assert result.exit_code == 0
        assert "[DRY RUN]" in result.output

        # Should NOT create files
        env_file = mock_project / ".env.uve"
        assert not env_file.exists()


def test_init_json_output(runner, mock_project, cache_file, monkeypatch):
    """Test that --json outputs valid JSON."""
    monkeypatch.chdir(mock_project)

    with patch(
        "prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file
    ):
        result = runner.invoke(cli, ["init", "--json"])

        assert result.exit_code == 0

        # Parse JSON
        data = json.loads(result.output)
        assert data["status"] == "success"
        assert "project" in data
        assert "venv" in data
        assert "env_file" in data
        assert "cache" in data


def test_init_yes_flag_skips_confirmation(
    runner, mock_project, cache_file, monkeypatch
):
    """Test that --yes skips confirmation prompts."""
    monkeypatch.chdir(mock_project)

    with patch(
        "prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file
    ):
        # First init
        runner.invoke(cli, ["init"])

        # Force with --yes should not prompt
        result = runner.invoke(cli, ["init", "--force", "--yes"])
        assert result.exit_code == 0
        # Should not contain confirmation text
        assert "Warning" not in result.output


def test_init_verbose_mode(runner, mock_project, cache_file, monkeypatch):
    """Test that --verbose shows detailed output."""
    monkeypatch.chdir(mock_project)

    with patch(
        "prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file
    ):
        result = runner.invoke(cli, ["init", "--verbose"])

        assert result.exit_code == 0
        # Verbose output should show more details
        output = result.output
        assert (
            "Project name:" in output
            or "Project root:" in output
            or "test" in output.lower()
        )


# Error Handling Tests


def test_init_not_in_project(runner, tmp_path, cache_file, monkeypatch):
    """Test error when not in a Python project."""
    # Directory without pyproject.toml
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    monkeypatch.chdir(empty_dir)

    with patch(
        "prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file
    ):
        result = runner.invoke(cli, ["init"])

        assert result.exit_code == 1
        assert "Not in a Python project" in result.output


def test_init_permission_denied_env_file(runner, mock_project, cache_file, monkeypatch):
    """Test error handling for .env.uve permission denied."""
    monkeypatch.chdir(mock_project)

    # Mock update_env_file_preserve_format to raise PermissionError
    def mock_update(*args, **kwargs):
        from prime_uve.core.env_file import EnvFileError

        raise EnvFileError("Permission denied")

    with patch(
        "prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file
    ):
        with patch(
            "prime_uve.cli.init.update_env_file_preserve_format",
            side_effect=mock_update,
        ):
            result = runner.invoke(cli, ["init"])

            assert result.exit_code == 2  # System error


def test_init_cache_write_failure(runner, mock_project, cache_file, monkeypatch):
    """Test error handling when cache write fails."""
    monkeypatch.chdir(mock_project)

    # Mock add_mapping to raise exception
    with patch(
        "prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file
    ):
        with patch(
            "prime_uve.core.cache.Cache.add_mapping",
            side_effect=Exception("Cache error"),
        ):
            result = runner.invoke(cli, ["init"])

            assert result.exit_code == 2  # System error


# Edge Cases Tests


def test_init_no_project_name_in_pyproject(runner, tmp_path, cache_file, monkeypatch):
    """Test fallback to directory name when pyproject has no name."""
    project_dir = tmp_path / "unnamed_project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    # pyproject.toml without name
    pyproject = project_dir / "pyproject.toml"
    pyproject.write_text('[project]\nversion = "0.1.0"\n')

    with patch(
        "prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file
    ):
        result = runner.invoke(cli, ["init"])

        assert result.exit_code == 0
        # Should use directory name
        assert "unnamed_project" in result.output or "unnamed-project" in result.output


def test_init_long_project_path(runner, tmp_path, cache_file, monkeypatch):
    """Test hash truncation with very long paths."""
    # Create deeply nested directory
    long_path = tmp_path
    for i in range(10):
        long_path = long_path / f"very_long_directory_name_{i}"
    long_path.mkdir(parents=True)

    project_dir = long_path / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    pyproject = project_dir / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test"\nversion = "0.1.0"\n')

    with patch(
        "prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file
    ):
        result = runner.invoke(cli, ["init"])

        # Should succeed - hash keeps venv path reasonable
        assert result.exit_code == 0

        env_file = project_dir / ".env.uve"
        content = env_file.read_text()

        # Venv path should be reasonable length (not thousands of chars)
        lines = content.split("\n")
        for line in lines:
            if line.startswith("UV_PROJECT_ENVIRONMENT="):
                # Path should be under 200 chars
                assert len(line) < 200
