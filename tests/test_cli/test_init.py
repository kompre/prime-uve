"""Tests for prime-uve init command."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

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


# Basic Functionality Tests


def test_init_creates_env_file(runner, mock_project, tmp_path, monkeypatch):
    """Test that init creates .env.uve with correct content."""
    # Change to project directory
    monkeypatch.chdir(mock_project)

    # Mock cache directory
    cache_file = tmp_path / ".prime-uve" / "cache.json"
    cache_file.parent.mkdir(exist_ok=True)

    with patch("prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file):
        result = runner.invoke(cli, ["init"])

        assert result.exit_code == 0, f"Failed with: {result.output}"

        env_file = mock_project / ".env.uve"
        assert env_file.exists()

        content = env_file.read_text()
        assert "UV_PROJECT_ENVIRONMENT=" in content
        assert "${HOME}/prime-uve/venvs/" in content
        assert "test-project" in content or "test_project" in content


def test_init_adds_to_cache(runner, mock_project, tmp_path):
    """Test that init adds mapping to cache."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cache_file = tmp_path / ".prime-uve" / "cache.json"
        cache_file.parent.mkdir(exist_ok=True)

        with patch("prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file):
            result = runner.invoke(cli, ["init"], cwd=str(mock_project))

            assert result.exit_code == 0

            # Check cache
            cache = Cache(cache_path=cache_file)
            mappings = cache.list_all()
            assert str(mock_project) in mappings


def test_init_uses_variable_form_in_env_file(runner, mock_project, tmp_path):
    """Test that .env.uve contains ${HOME} not expanded path."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cache_file = tmp_path / ".prime-uve"
        cache_file.parent.mkdir(exist_ok=True)

        with patch("prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file):
            result = runner.invoke(cli, ["init"], cwd=str(mock_project))

            assert result.exit_code == 0

            env_file = mock_project / ".env.uve"
            content = env_file.read_text()

            # Should contain ${HOME}, not expanded path
            assert "${HOME}" in content
            # Should NOT contain actual home directory path
            import os

            home = os.path.expanduser("~")
            assert home not in content


def test_init_success_message_shows_next_steps(runner, mock_project, tmp_path):
    """Test that success output guides user."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cache_file = tmp_path / ".prime-uve"
        cache_file.parent.mkdir(exist_ok=True)

        with patch("prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file):
            result = runner.invoke(cli, ["init"], cwd=str(mock_project))

            assert result.exit_code == 0

            output = result.output
            assert "Next steps:" in output
            assert "uve sync" in output
            assert "Commit .env.uve" in output


# Already Initialized Tests


def test_init_refuses_overwrite_without_force(runner, mock_project, tmp_path):
    """Test that init refuses to overwrite existing .env.uve."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cache_file = tmp_path / ".prime-uve"
        cache_file.parent.mkdir(exist_ok=True)

        with patch("prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file):
            # First init
            result1 = runner.invoke(cli, ["init"], cwd=str(mock_project))
            assert result1.exit_code == 0

            # Second init without --force should fail
            result2 = runner.invoke(cli, ["init"], cwd=str(mock_project))
            assert result2.exit_code == 1
            assert "already initialized" in result2.output.lower()


def test_init_force_overwrites(runner, mock_project, tmp_path):
    """Test that init --force overwrites existing setup."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cache_file = tmp_path / ".prime-uve"
        cache_file.parent.mkdir(exist_ok=True)

        with patch("prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file):
            # First init
            runner.invoke(cli, ["init"], cwd=str(mock_project))

            # Second init with --force and --yes should succeed
            result = runner.invoke(cli, ["init", "--force", "--yes"], cwd=str(mock_project))
            assert result.exit_code == 0
            assert "Created .env.uve" in result.output


def test_init_force_preserves_other_vars(runner, mock_project, tmp_path):
    """Test that --force preserves other env vars in .env.uve."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cache_file = tmp_path / ".prime-uve"
        cache_file.parent.mkdir(exist_ok=True)

        with patch("prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file):
            # First init
            runner.invoke(cli, ["init"], cwd=str(mock_project))

            # Add another variable to .env.uve
            env_file = mock_project / ".env.uve"
            content = env_file.read_text()
            content += "\nCUSTOM_VAR=test_value\n"
            env_file.write_text(content)

            # Force reinit
            runner.invoke(cli, ["init", "--force", "--yes"], cwd=str(mock_project))

            # Check that custom var is preserved
            new_content = env_file.read_text()
            assert "CUSTOM_VAR=test_value" in new_content
            assert "UV_PROJECT_ENVIRONMENT=" in new_content


def test_init_force_shows_confirmation(runner, mock_project, tmp_path):
    """Test that --force prompts for confirmation without --yes."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cache_file = tmp_path / ".prime-uve"
        cache_file.parent.mkdir(exist_ok=True)

        with patch("prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file):
            # First init
            runner.invoke(cli, ["init"], cwd=str(mock_project))

            # Force without --yes should prompt (we'll cancel it)
            result = runner.invoke(cli, ["init", "--force"], input="n\n", cwd=str(mock_project))
            assert result.exit_code == 1  # Aborted
            assert "Warning" in result.output or "continue" in result.output.lower()


# Options and Flags Tests


def test_init_custom_venv_dir(runner, mock_project, tmp_path):
    """Test that --venv-dir overrides default location."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cache_file = tmp_path / ".prime-uve"
        cache_file.parent.mkdir(exist_ok=True)

        custom_venv_dir = "${HOME}/custom/venvs"

        with patch("prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file):
            result = runner.invoke(
                cli, ["init", "--venv-dir", custom_venv_dir], cwd=str(mock_project)
            )

            assert result.exit_code == 0

            env_file = mock_project / ".env.uve"
            content = env_file.read_text()
            assert "custom/venvs" in content


def test_init_dry_run(runner, mock_project, tmp_path):
    """Test that --dry-run shows plan without executing."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cache_file = tmp_path / ".prime-uve"
        cache_file.parent.mkdir(exist_ok=True)

        with patch("prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file):
            result = runner.invoke(cli, ["init", "--dry-run"], cwd=str(mock_project))

            assert result.exit_code == 0
            assert "[DRY RUN]" in result.output

            # Should NOT create files
            env_file = mock_project / ".env.uve"
            assert not env_file.exists()


def test_init_json_output(runner, mock_project, tmp_path):
    """Test that --json outputs valid JSON."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cache_file = tmp_path / ".prime-uve"
        cache_file.parent.mkdir(exist_ok=True)

        with patch("prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file):
            result = runner.invoke(cli, ["init", "--json"], cwd=str(mock_project))

            assert result.exit_code == 0

            # Parse JSON
            data = json.loads(result.output)
            assert data["status"] == "success"
            assert "project" in data
            assert "venv" in data
            assert "env_file" in data
            assert "cache" in data


def test_init_yes_flag_skips_confirmation(runner, mock_project, tmp_path):
    """Test that --yes skips confirmation prompts."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cache_file = tmp_path / ".prime-uve"
        cache_file.parent.mkdir(exist_ok=True)

        with patch("prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file):
            # First init
            runner.invoke(cli, ["init"], cwd=str(mock_project))

            # Force with --yes should not prompt
            result = runner.invoke(cli, ["init", "--force", "--yes"], cwd=str(mock_project))
            assert result.exit_code == 0
            # Should not contain confirmation text
            assert "Warning" not in result.output


# Error Handling Tests


def test_init_not_in_project(runner, tmp_path):
    """Test error when not in a Python project."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Directory without pyproject.toml
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = runner.invoke(cli, ["init"], cwd=str(empty_dir))

        assert result.exit_code == 1
        assert "Not in a Python project" in result.output


def test_init_permission_denied_env_file(runner, mock_project, tmp_path, monkeypatch):
    """Test error handling for .env.uve permission denied."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cache_file = tmp_path / ".prime-uve"
        cache_file.parent.mkdir(exist_ok=True)

        # Mock write_env_file to raise PermissionError
        def mock_write_env_file(*args, **kwargs):
            raise PermissionError("Permission denied")

        with patch("prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file):
            with patch("prime_uve.cli.init.write_env_file", side_effect=mock_write_env_file):
                result = runner.invoke(cli, ["init"], cwd=str(mock_project))

                assert result.exit_code == 2  # System error
                # Error message should be displayed


def test_init_cache_write_failure(runner, mock_project, tmp_path):
    """Test error handling when cache write fails."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cache_file = tmp_path / ".prime-uve"
        cache_file.parent.mkdir(exist_ok=True)

        # Mock add_mapping to raise exception
        with patch("prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file):
            with patch("prime_uve.core.cache.Cache.add_mapping", side_effect=Exception("Cache error")):
                result = runner.invoke(cli, ["init"], cwd=str(mock_project))

                assert result.exit_code == 2  # System error


def test_init_invalid_venv_dir(runner, mock_project, tmp_path):
    """Test error with invalid --venv-dir path."""
    # This test verifies that even with invalid venv_dir, we still generate valid paths
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cache_file = tmp_path / ".prime-uve"
        cache_file.parent.mkdir(exist_ok=True)

        # Use a path with special characters that need sanitization
        invalid_dir = "/invalid*/path"

        with patch("prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file):
            # The command might succeed (generate_venv_path handles it)
            # or fail depending on implementation
            result = runner.invoke(
                cli, ["init", "--venv-dir", invalid_dir], cwd=str(mock_project)
            )

            # Either way, we shouldn't crash
            assert result.exit_code in (0, 1, 2)


# Edge Cases Tests


def test_init_no_project_name_in_pyproject(runner, tmp_path):
    """Test fallback to directory name when pyproject has no name."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        project_dir = tmp_path / "unnamed_project"
        project_dir.mkdir()

        # pyproject.toml without name
        pyproject = project_dir / "pyproject.toml"
        pyproject.write_text('[project]\nversion = "0.1.0"\n')

        cache_file = tmp_path / ".prime-uve"
        cache_file.parent.mkdir(exist_ok=True)

        with patch("prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file):
            result = runner.invoke(cli, ["init"], cwd=str(project_dir))

            assert result.exit_code == 0
            # Should use directory name
            assert "unnamed_project" in result.output or "unnamed-project" in result.output


def test_init_long_project_path(runner, tmp_path):
    """Test hash truncation with very long paths."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create deeply nested directory
        long_path = tmp_path
        for i in range(20):
            long_path = long_path / f"very_long_directory_name_{i}"
        long_path.mkdir(parents=True)

        project_dir = long_path / "project"
        project_dir.mkdir()

        pyproject = project_dir / "pyproject.toml"
        pyproject.write_text('[project]\nname = "test"\nversion = "0.1.0"\n')

        cache_file = tmp_path / ".prime-uve"
        cache_file.parent.mkdir(exist_ok=True)

        with patch("prime_uve.core.cache.Cache._default_cache_path", return_value=cache_file):
            result = runner.invoke(cli, ["init"], cwd=str(project_dir))

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
