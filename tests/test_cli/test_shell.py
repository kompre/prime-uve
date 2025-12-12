"""Tests for prime-uve shell command."""

import sys
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from prime_uve.cli.main import cli


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_project_with_venv(tmp_path):
    """Create a mock Python project with venv."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create pyproject.toml
    pyproject = project_dir / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-project"\nversion = "0.1.0"\n')

    # Create venv directory
    venv_dir = tmp_path / "venvs" / "test-project_abc123"
    venv_dir.mkdir(parents=True)

    # Create bin/Scripts directory
    if sys.platform == "win32":
        bin_dir = venv_dir / "Scripts"
    else:
        bin_dir = venv_dir / "bin"
    bin_dir.mkdir(exist_ok=True)

    # Create .env.uve with venv path
    env_file = project_dir / ".env.uve"
    env_file.write_text(
        f"UV_PROJECT_ENVIRONMENT={venv_dir}\n"
        f"DATABASE_URL=postgresql://localhost/db\n"
        f"API_KEY=secret123\n"
    )

    return {
        "project_dir": project_dir,
        "venv_dir": venv_dir,
        "env_file": env_file,
    }


# Basic Functionality Tests


def test_shell_spawns_subprocess(runner, mock_project_with_venv, monkeypatch):
    """Test that shell command spawns a subprocess."""
    monkeypatch.chdir(mock_project_with_venv["project_dir"])
    monkeypatch.setenv("SHELL", "/bin/bash")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = runner.invoke(cli, ["shell"])

        assert result.exit_code == 0
        # Verify subprocess.run was called
        assert mock_run.called


def test_shell_sets_virtual_env(runner, mock_project_with_venv, monkeypatch):
    """Test that VIRTUAL_ENV is set in spawned shell."""
    monkeypatch.chdir(mock_project_with_venv["project_dir"])
    monkeypatch.setenv("SHELL", "/bin/bash")
    venv_path = str(mock_project_with_venv["venv_dir"])

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = runner.invoke(cli, ["shell"])

        assert result.exit_code == 0
        # Check that env passed to subprocess.run contains VIRTUAL_ENV
        call_kwargs = mock_run.call_args[1]
        env = call_kwargs["env"]
        assert "VIRTUAL_ENV" in env
        assert env["VIRTUAL_ENV"] == venv_path


def test_shell_exports_all_env_vars(runner, mock_project_with_venv, monkeypatch):
    """Test that all variables from .env.uve are exported."""
    monkeypatch.chdir(mock_project_with_venv["project_dir"])
    monkeypatch.setenv("SHELL", "/bin/bash")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = runner.invoke(cli, ["shell"])

        assert result.exit_code == 0
        call_kwargs = mock_run.call_args[1]
        env = call_kwargs["env"]
        assert "DATABASE_URL" in env
        assert env["DATABASE_URL"] == "postgresql://localhost/db"
        assert "API_KEY" in env
        assert env["API_KEY"] == "secret123"


def test_shell_modifies_path(runner, mock_project_with_venv, monkeypatch):
    """Test that venv bin/Scripts is prepended to PATH."""
    monkeypatch.chdir(mock_project_with_venv["project_dir"])
    monkeypatch.setenv("SHELL", "/bin/bash")
    monkeypatch.setenv("PATH", "/usr/bin:/bin")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = runner.invoke(cli, ["shell"])

        assert result.exit_code == 0
        call_kwargs = mock_run.call_args[1]
        env = call_kwargs["env"]
        assert "PATH" in env
        # Venv bin/Scripts should be at the start of PATH
        venv_dir = mock_project_with_venv["venv_dir"]
        if sys.platform == "win32":
            expected_prefix = str(venv_dir / "Scripts")
        else:
            expected_prefix = str(venv_dir / "bin")
        assert env["PATH"].startswith(expected_prefix)


# Shell Detection Tests


def test_shell_auto_detects_bash(runner, mock_project_with_venv, monkeypatch):
    """Test shell auto-detection for bash."""
    monkeypatch.chdir(mock_project_with_venv["project_dir"])
    monkeypatch.setenv("SHELL", "/bin/bash")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = runner.invoke(cli, ["shell"])

        assert result.exit_code == 0
        call_args = mock_run.call_args[0][0]
        assert "bash" in call_args


def test_shell_override_works(runner, mock_project_with_venv, monkeypatch):
    """Test --shell override option."""
    monkeypatch.chdir(mock_project_with_venv["project_dir"])
    monkeypatch.setenv("SHELL", "/bin/bash")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = runner.invoke(cli, ["shell", "--shell", "zsh"])

        assert result.exit_code == 0
        call_args = mock_run.call_args[0][0]
        assert "zsh" in call_args


# Error Handling Tests


def test_shell_not_in_project(runner, tmp_path, monkeypatch):
    """Test error when not in a project."""
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(cli, ["shell"])

    assert result.exit_code != 0
    assert "Not in a Python project" in result.output


def test_shell_no_env_file(runner, tmp_path, monkeypatch):
    """Test error when .env.uve doesn't exist."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    pyproject = project_dir / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-project"\n')

    monkeypatch.chdir(project_dir)

    result = runner.invoke(cli, ["shell"])

    assert result.exit_code != 0
    assert (
        "not initialized" in result.output.lower()
        or "no .env.uve" in result.output.lower()
    )


def test_shell_venv_doesnt_exist(runner, tmp_path, monkeypatch):
    """Test error when venv doesn't exist."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    pyproject = project_dir / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-project"\n')

    non_existent_venv = tmp_path / "venvs" / "nonexistent"
    env_file = project_dir / ".env.uve"
    env_file.write_text(f"UV_PROJECT_ENVIRONMENT={non_existent_venv}\n")

    monkeypatch.chdir(project_dir)

    result = runner.invoke(cli, ["shell"])

    assert result.exit_code != 0
    assert "not found" in result.output.lower() or "venv" in result.output.lower()


def test_shell_missing_bin_directory(runner, tmp_path, monkeypatch):
    """Test error when venv bin/Scripts directory is missing."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    pyproject = project_dir / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-project"\n')

    # Create venv dir but no bin/Scripts
    venv_dir = tmp_path / "venvs" / "test-project_abc123"
    venv_dir.mkdir(parents=True)

    env_file = project_dir / ".env.uve"
    env_file.write_text(f"UV_PROJECT_ENVIRONMENT={venv_dir}\n")

    monkeypatch.chdir(project_dir)

    result = runner.invoke(cli, ["shell"])

    assert result.exit_code != 0
    assert "not found" in result.output.lower() or "corrupted" in result.output.lower()


def test_shell_command_not_found(runner, mock_project_with_venv, monkeypatch):
    """Test error when shell executable is not found."""
    monkeypatch.chdir(mock_project_with_venv["project_dir"])

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("Shell not found")
        result = runner.invoke(cli, ["shell", "--shell", "nonexistent-shell"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "shell" in result.output.lower()


# Verbose Mode Tests


def test_shell_verbose_mode(runner, mock_project_with_venv, monkeypatch):
    """Test --verbose shows diagnostic info."""
    monkeypatch.chdir(mock_project_with_venv["project_dir"])
    monkeypatch.setenv("SHELL", "/bin/bash")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = runner.invoke(cli, ["shell", "--verbose"])

        assert result.exit_code == 0
        # Verbose output should mention spawning shell
        assert "spawning" in result.output.lower() or "shell" in result.output.lower()


# Variable Expansion Tests


def test_shell_expands_variables(runner, mock_project_with_venv, monkeypatch, tmp_path):
    """Test that variables like ${HOME} are expanded in environment."""
    venv_relative = str(mock_project_with_venv["venv_dir"]).replace(
        str(tmp_path), "${HOME}"
    )

    env_file = mock_project_with_venv["env_file"]
    env_file.write_text(f"UV_PROJECT_ENVIRONMENT={venv_relative}\n")

    monkeypatch.chdir(mock_project_with_venv["project_dir"])
    monkeypatch.setenv("SHELL", "/bin/bash")
    monkeypatch.setenv("HOME", str(tmp_path))

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = runner.invoke(cli, ["shell"])

        assert result.exit_code == 0
        call_kwargs = mock_run.call_args[1]
        env = call_kwargs["env"]
        # UV_PROJECT_ENVIRONMENT should be expanded
        assert "${HOME}" not in env["UV_PROJECT_ENVIRONMENT"]
        assert str(mock_project_with_venv["venv_dir"]) == env["UV_PROJECT_ENVIRONMENT"]


# Windows-Specific Tests


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_shell_sets_home_on_windows(runner, mock_project_with_venv, monkeypatch):
    """Test that HOME is set on Windows if missing."""
    monkeypatch.chdir(mock_project_with_venv["project_dir"])
    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.delenv("HOME", raising=False)
    monkeypatch.setenv("USERPROFILE", "C:\\Users\\testuser")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = runner.invoke(cli, ["shell"])

        assert result.exit_code == 0
        call_kwargs = mock_run.call_args[1]
        env = call_kwargs["env"]
        assert "HOME" in env
        assert env["HOME"] == "C:\\Users\\testuser"
