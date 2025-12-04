"""Tests for CLI output utilities."""

import json

import click
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

        @click.command()
        def test_cmd():
            success("Test success")

        result = runner.invoke(test_cmd)
        # Check for checkmark in output
        assert "✓" in result.output or "Test success" in result.output

    def test_error_message(self):
        """Test error message formatting."""
        runner = CliRunner()

        @click.command()
        def test_cmd():
            error("Test error")

        result = runner.invoke(test_cmd)
        # Check for X mark in output
        assert "✗" in result.output or "Test error" in result.output

    def test_warning_message(self):
        """Test warning message formatting."""
        runner = CliRunner()

        @click.command()
        def test_cmd():
            warning("Test warning")

        result = runner.invoke(test_cmd)
        # Check for warning symbol in output
        assert "⚠" in result.output or "Test warning" in result.output

    def test_info_message(self):
        """Test info message formatting."""
        runner = CliRunner()

        @click.command()
        def test_cmd():
            info("Test info")

        result = runner.invoke(test_cmd)
        # Check for info symbol in output
        assert "ℹ" in result.output or "Test info" in result.output

    def test_print_json(self):
        """Test JSON output formatting."""
        data = {"key": "value", "number": 42}
        runner = CliRunner()

        @click.command()
        def test_cmd():
            print_json(data)

        result = runner.invoke(test_cmd)
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

        @click.command()
        def test_cmd():
            result = confirm("Are you sure?", yes_flag=False)
            echo(f"Result: {result}")

        # Simulate user pressing 'y'
        result = runner.invoke(test_cmd, input="y\n")
        assert "Result: True" in result.output

    def test_echo(self):
        """Test echo wrapper."""
        runner = CliRunner()

        @click.command()
        def test_cmd():
            echo("Test message")

        result = runner.invoke(test_cmd)
        assert "Test message" in result.output
