"""Tests for CLI main module."""

import pytest
from click.testing import CliRunner

from prime_uve.cli.main import cli, get_version


class TestCLIMain:
    """Test main CLI functionality."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner."""
        return CliRunner()

    def test_cli_help(self, runner):
        """Test that --help displays help message."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "prime-uve" in result.output
        assert "Virtual environment management" in result.output

    def test_cli_version(self, runner):
        """Test that --version displays version."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "prime-uve" in result.output

    def test_get_version(self):
        """Test version extraction from pyproject.toml."""
        version = get_version()
        assert version is not None
        # Should either be a version string or "unknown"
        assert isinstance(version, str)

    def test_init_command_exists(self, runner):
        """Test that init command exists."""
        result = runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0
        assert "Initialize project" in result.output

    def test_list_command_exists(self, runner):
        """Test that list command exists."""
        result = runner.invoke(cli, ["list", "--help"])
        assert result.exit_code == 0
        assert "List all managed venvs" in result.output

    def test_prune_command_exists(self, runner):
        """Test that prune command exists."""
        result = runner.invoke(cli, ["prune", "--help"])
        assert result.exit_code == 0
        assert "Clean up venv" in result.output

    def test_activate_command_exists(self, runner):
        """Test that activate command exists."""
        result = runner.invoke(cli, ["activate", "--help"])
        assert result.exit_code == 0
        assert "Output activation command" in result.output

    def test_configure_group_exists(self, runner):
        """Test that configure group exists."""
        result = runner.invoke(cli, ["configure", "--help"])
        assert result.exit_code == 0
        assert "Configure integrations" in result.output

    def test_configure_vscode_command_exists(self, runner):
        """Test that configure vscode command exists."""
        result = runner.invoke(cli, ["configure", "vscode", "--help"])
        assert result.exit_code == 0
        assert "VS Code workspace" in result.output

    def test_common_options_on_commands(self, runner):
        """Test that commands have common options."""
        for command in ["init", "list", "prune", "activate"]:
            result = runner.invoke(cli, [command, "--help"])
            assert "--verbose" in result.output
            assert "--yes" in result.output
            assert "--dry-run" in result.output
            assert "--json" in result.output

    def test_unimplemented_commands_return_error(self, runner):
        """Test that unimplemented commands exit with error code."""
        # Test only unimplemented subcommands
        # Note: configure vscode is a subcommand, not a top-level command
        result = runner.invoke(cli, ["configure", "vscode"])
        assert result.exit_code == 1
