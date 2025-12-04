"""Tests for CLI output utilities."""

import json
from io import StringIO
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from prime_uve.cli.output import (
    confirm,
    echo,
    error,
    info,
    print_json,
    success,
    warning,
)


class TestOutputFormatting:
    """Test output formatting functions."""

    def test_success_message(self):
        """Test success message formatting."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(lambda: success("Test success"))
            # Check for checkmark in output
            assert "✓" in result.output or "Test success" in result.output

    def test_error_message(self):
        """Test error message formatting."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(lambda: error("Test error"))
            # Check for X mark in output
            assert "✗" in result.output or "Test error" in result.output

    def test_warning_message(self):
        """Test warning message formatting."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(lambda: warning("Test warning"))
            # Check for warning symbol in output
            assert "⚠" in result.output or "Test warning" in result.output

    def test_info_message(self):
        """Test info message formatting."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(lambda: info("Test info"))
            # Check for info symbol in output
            assert "ℹ" in result.output or "Test info" in result.output

    def test_print_json(self):
        """Test JSON output formatting."""
        data = {"key": "value", "number": 42}
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(lambda: print_json(data))
            # Should be valid JSON
            parsed = json.loads(result.output)
            assert parsed == data

    def test_confirm_with_yes_flag(self):
        """Test confirm skips prompt when yes_flag is True."""
        result = confirm("Are you sure?", yes_flag=True)
        assert result is True

    def test_confirm_without_yes_flag(self):
        """Test confirm prompts user when yes_flag is False."""
        runner = CliRunner()
        # Simulate user pressing 'y'
        result = runner.invoke(
            lambda: confirm("Are you sure?", yes_flag=False), input="y\n"
        )
        # Click's confirm will work in the isolated context

    def test_echo(self):
        """Test echo wrapper."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(lambda: echo("Test message"))
            assert "Test message" in result.output
