"""Tests for prime-uve activate command."""

import sys
from unittest.mock import patch

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

    # Create activation scripts
    bin_dir = venv_dir / "bin"
    bin_dir.mkdir(exist_ok=True)
    (bin_dir / "activate").write_text("# bash activation")
    (bin_dir / "activate.fish").write_text("# fish activation")

    scripts_dir = venv_dir / "Scripts"
    scripts_dir.mkdir(exist_ok=True)
    (scripts_dir / "Activate.ps1").write_text("# PowerShell activation")
    (scripts_dir / "activate.bat").write_text("@echo off")

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


def test_activate_bash_output(runner, mock_project_with_venv, monkeypatch):
    """Test activate generates correct bash commands."""
    monkeypatch.chdir(mock_project_with_venv["project_dir"])
    monkeypatch.setenv("SHELL", "/bin/bash")

    result = runner.invoke(cli, ["activate"])

    assert result.exit_code == 0, f"Failed with: {result.output}"
    assert "export UV_PROJECT_ENVIRONMENT=" in result.output
    assert "export DATABASE_URL=" in result.output
    assert "export API_KEY=" in result.output
    assert "source" in result.output
    # Use os-agnostic path check (Windows uses backslashes)
    assert "activate" in result.output and (
        "bin" in result.output or "Scripts" in result.output
    )


def test_activate_zsh_output(runner, mock_project_with_venv, monkeypatch):
    """Test activate generates correct zsh commands."""
    monkeypatch.chdir(mock_project_with_venv["project_dir"])
    monkeypatch.setenv("SHELL", "/usr/bin/zsh")

    result = runner.invoke(cli, ["activate"])

    assert result.exit_code == 0
    assert "export UV_PROJECT_ENVIRONMENT=" in result.output
    assert "source" in result.output
    # Use os-agnostic path check
    assert "activate" in result.output


def test_activate_fish_output(runner, mock_project_with_venv, monkeypatch):
    """Test activate generates correct fish commands."""
    monkeypatch.chdir(mock_project_with_venv["project_dir"])
    monkeypatch.setenv("SHELL", "/usr/local/bin/fish")

    result = runner.invoke(cli, ["activate"])

    assert result.exit_code == 0
    assert "set -x UV_PROJECT_ENVIRONMENT" in result.output
    assert "set -x DATABASE_URL" in result.output
    assert "set -x API_KEY" in result.output
    assert "source" in result.output
    assert "activate.fish" in result.output


def test_activate_powershell_output(runner, mock_project_with_venv, monkeypatch):
    """Test activate generates correct PowerShell commands."""
    monkeypatch.chdir(mock_project_with_venv["project_dir"])
    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.setenv("PSModulePath", "C:\\PowerShell\\Modules")

    with patch.object(sys, "platform", "win32"):
        result = runner.invoke(cli, ["activate", "--shell", "pwsh"])

        assert result.exit_code == 0, f"Failed with: {result.output}"
        assert "$env:UV_PROJECT_ENVIRONMENT=" in result.output
        assert "$env:DATABASE_URL=" in result.output
        assert "$env:API_KEY=" in result.output
        assert "if (-not $env:HOME)" in result.output
        assert "Activate.ps1" in result.output


def test_activate_exports_all_env_vars(runner, mock_project_with_venv, monkeypatch):
    """Test that ALL variables from .env.uve are exported."""
    monkeypatch.chdir(mock_project_with_venv["project_dir"])
    monkeypatch.setenv("SHELL", "/bin/bash")

    result = runner.invoke(cli, ["activate"])

    assert result.exit_code == 0
    # Check all three variables are exported
    assert "UV_PROJECT_ENVIRONMENT=" in result.output
    assert "DATABASE_URL=" in result.output
    assert "API_KEY=" in result.output


# Shell Detection and Override Tests


def test_activate_shell_override(runner, mock_project_with_venv, monkeypatch):
    """Test --shell override works."""
    monkeypatch.chdir(mock_project_with_venv["project_dir"])
    monkeypatch.setenv("SHELL", "/bin/bash")  # Set bash

    # Override to fish
    result = runner.invoke(cli, ["activate", "--shell", "fish"])

    assert result.exit_code == 0
    # Should use fish syntax despite bash being detected
    assert "set -x" in result.output
    assert "activate.fish" in result.output


def test_activate_auto_detect_bash(runner, mock_project_with_venv, monkeypatch):
    """Test auto-detection of bash from SHELL env var."""
    monkeypatch.chdir(mock_project_with_venv["project_dir"])
    monkeypatch.setenv("SHELL", "/bin/bash")

    result = runner.invoke(cli, ["activate"])

    assert result.exit_code == 0
    assert "export" in result.output


def test_activate_auto_detect_zsh(runner, mock_project_with_venv, monkeypatch):
    """Test auto-detection of zsh from SHELL env var."""
    monkeypatch.chdir(mock_project_with_venv["project_dir"])
    monkeypatch.setenv("SHELL", "/usr/bin/zsh")

    result = runner.invoke(cli, ["activate"])

    assert result.exit_code == 0
    assert "export" in result.output


# Error Handling Tests


def test_activate_not_in_project(runner, tmp_path, monkeypatch):
    """Test error when not in a project."""
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(cli, ["activate"])

    assert result.exit_code != 0
    assert "Not in a Python project" in result.output


def test_activate_no_env_file(runner, tmp_path, monkeypatch):
    """Test error when .env.uve doesn't exist."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create pyproject.toml but no .env.uve
    pyproject = project_dir / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-project"\n')

    monkeypatch.chdir(project_dir)

    result = runner.invoke(cli, ["activate"])

    assert result.exit_code != 0
    assert (
        "not initialized" in result.output.lower()
        or "no .env.uve" in result.output.lower()
    )


def test_activate_empty_env_file(runner, tmp_path, monkeypatch):
    """Test error when .env.uve is empty."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    pyproject = project_dir / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-project"\n')

    env_file = project_dir / ".env.uve"
    env_file.write_text("")  # Empty file

    monkeypatch.chdir(project_dir)

    result = runner.invoke(cli, ["activate"])

    assert result.exit_code != 0
    assert "empty" in result.output.lower() or "init" in result.output.lower()


def test_activate_missing_uv_project_environment(runner, tmp_path, monkeypatch):
    """Test error when .env.uve is missing UV_PROJECT_ENVIRONMENT."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    pyproject = project_dir / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-project"\n')

    env_file = project_dir / ".env.uve"
    env_file.write_text("SOME_OTHER_VAR=value\n")  # Missing UV_PROJECT_ENVIRONMENT

    monkeypatch.chdir(project_dir)

    result = runner.invoke(cli, ["activate"])

    assert result.exit_code != 0
    assert "UV_PROJECT_ENVIRONMENT" in result.output


def test_activate_venv_doesnt_exist(runner, tmp_path, monkeypatch):
    """Test error when venv doesn't exist."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    pyproject = project_dir / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-project"\n')

    # Point to non-existent venv
    non_existent_venv = tmp_path / "venvs" / "nonexistent"
    env_file = project_dir / ".env.uve"
    env_file.write_text(f"UV_PROJECT_ENVIRONMENT={non_existent_venv}\n")

    monkeypatch.chdir(project_dir)

    result = runner.invoke(cli, ["activate"])

    assert result.exit_code != 0
    assert "not found" in result.output.lower() or "venv" in result.output.lower()


# Variable Expansion Tests


def test_activate_expands_home_for_activation(
    runner, mock_project_with_venv, monkeypatch, tmp_path
):
    """Test that ${HOME} is expanded in venv path for activation."""
    # Update .env.uve to use ${HOME} variable
    env_file = mock_project_with_venv["env_file"]
    venv_relative = str(mock_project_with_venv["venv_dir"]).replace(
        str(tmp_path), "${HOME}"
    )

    env_file.write_text(
        f"UV_PROJECT_ENVIRONMENT={venv_relative}\n"
        f"DATABASE_URL=postgresql://localhost/db\n"
    )

    monkeypatch.chdir(mock_project_with_venv["project_dir"])
    monkeypatch.setenv("SHELL", "/bin/bash")
    monkeypatch.setenv("HOME", str(tmp_path))

    result = runner.invoke(cli, ["activate"])

    assert result.exit_code == 0
    # Should still work because expansion happens for activation


def test_activate_keeps_variables_unexpanded_in_exports(
    runner, mock_project_with_venv, monkeypatch, tmp_path
):
    """Test that variables remain unexpanded in export commands."""
    # Use ${HOME} in the venv path
    venv_relative = str(mock_project_with_venv["venv_dir"]).replace(
        str(tmp_path), "${HOME}"
    )

    env_file = mock_project_with_venv["env_file"]
    env_file.write_text(f"UV_PROJECT_ENVIRONMENT={venv_relative}\n")

    monkeypatch.chdir(mock_project_with_venv["project_dir"])
    monkeypatch.setenv("SHELL", "/bin/bash")
    monkeypatch.setenv("HOME", str(tmp_path))

    result = runner.invoke(cli, ["activate"])

    assert result.exit_code == 0
    # Export should keep ${HOME} syntax
    assert "${HOME}" in result.output or venv_relative in result.output


# Verbose Mode Tests


def test_activate_verbose_mode(runner, mock_project_with_venv, monkeypatch):
    """Test --verbose shows diagnostic info."""
    monkeypatch.chdir(mock_project_with_venv["project_dir"])
    monkeypatch.setenv("SHELL", "/bin/bash")

    result = runner.invoke(cli, ["activate", "--verbose"])

    assert result.exit_code == 0
    # Verbose output goes to stderr in real usage, but CliRunner captures it
    # Check that activation commands are still in output
    assert "export" in result.output or "[INFO]" in result.output


# Integration Tests


def test_activate_with_multiple_env_vars(runner, mock_project_with_venv, monkeypatch):
    """Test exporting multiple environment variables."""
    # Add more variables to .env.uve
    env_file = mock_project_with_venv["env_file"]
    venv_dir = mock_project_with_venv["venv_dir"]

    env_file.write_text(
        f"UV_PROJECT_ENVIRONMENT={venv_dir}\nVAR1=value1\nVAR2=value2\nVAR3=value3\n"
    )

    monkeypatch.chdir(mock_project_with_venv["project_dir"])
    monkeypatch.setenv("SHELL", "/bin/bash")

    result = runner.invoke(cli, ["activate"])

    assert result.exit_code == 0
    assert "VAR1=" in result.output
    assert "VAR2=" in result.output
    assert "VAR3=" in result.output


def test_activate_cmd_on_windows(runner, mock_project_with_venv, monkeypatch):
    """Test cmd activation on Windows."""
    monkeypatch.chdir(mock_project_with_venv["project_dir"])
    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.delenv("PSModulePath", raising=False)

    with patch.object(sys, "platform", "win32"):
        result = runner.invoke(cli, ["activate", "--shell", "cmd"])

        assert result.exit_code == 0
        assert "set UV_PROJECT_ENVIRONMENT=" in result.output
        assert "call" in result.output
        assert "activate.bat" in result.output
        # Check for HOME setup
        assert "HOME" in result.output
