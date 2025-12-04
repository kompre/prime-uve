"""Tests for CLI decorators."""


import click
from click.testing import CliRunner

from prime_uve.cli.decorators import common_options, handle_errors


class TestCommonOptions:
    """Test common_options decorator."""

    def test_common_options_adds_verbose(self):
        """Test that common_options adds --verbose flag."""

        @click.command()
        @common_options
        def test_cmd(verbose, yes, dry_run, json_output):
            if verbose:
                click.echo("verbose enabled")

        runner = CliRunner()
        result = runner.invoke(test_cmd, ["--verbose"])
        assert result.exit_code == 0
        assert "verbose enabled" in result.output

    def test_common_options_adds_yes(self):
        """Test that common_options adds --yes flag."""

        @click.command()
        @common_options
        def test_cmd(verbose, yes, dry_run, json_output):
            if yes:
                click.echo("yes enabled")

        runner = CliRunner()
        result = runner.invoke(test_cmd, ["--yes"])
        assert result.exit_code == 0
        assert "yes enabled" in result.output

    def test_common_options_adds_dry_run(self):
        """Test that common_options adds --dry-run flag."""

        @click.command()
        @common_options
        def test_cmd(verbose, yes, dry_run, json_output):
            if dry_run:
                click.echo("dry-run enabled")

        runner = CliRunner()
        result = runner.invoke(test_cmd, ["--dry-run"])
        assert result.exit_code == 0
        assert "dry-run enabled" in result.output

    def test_common_options_adds_json(self):
        """Test that common_options adds --json flag."""

        @click.command()
        @common_options
        def test_cmd(verbose, yes, dry_run, json_output):
            if json_output:
                click.echo("json enabled")

        runner = CliRunner()
        result = runner.invoke(test_cmd, ["--json"])
        assert result.exit_code == 0
        assert "json enabled" in result.output

    def test_common_options_short_flags(self):
        """Test that short flags work (-v, -y)."""

        @click.command()
        @common_options
        def test_cmd(verbose, yes, dry_run, json_output):
            if verbose and yes:
                click.echo("both enabled")

        runner = CliRunner()
        result = runner.invoke(test_cmd, ["-v", "-y"])
        assert result.exit_code == 0
        assert "both enabled" in result.output


class TestHandleErrors:
    """Test handle_errors decorator."""

    def test_handle_errors_success(self):
        """Test that successful execution returns normally."""

        @click.command()
        @handle_errors
        def test_cmd():
            click.echo("success")
            return 0

        runner = CliRunner()
        result = runner.invoke(test_cmd)
        assert result.exit_code == 0
        assert "success" in result.output

    def test_handle_errors_file_not_found(self):
        """Test that FileNotFoundError is handled with exit code 1."""

        @click.command()
        @handle_errors
        def test_cmd():
            raise FileNotFoundError("test.txt")

        runner = CliRunner()
        result = runner.invoke(test_cmd)
        assert result.exit_code == 1
        assert "File not found" in result.output

    def test_handle_errors_permission_error(self):
        """Test that PermissionError is handled with exit code 2."""

        @click.command()
        @handle_errors
        def test_cmd():
            raise PermissionError("Access denied")

        runner = CliRunner()
        result = runner.invoke(test_cmd)
        assert result.exit_code == 2
        assert "Permission denied" in result.output

    def test_handle_errors_value_error(self):
        """Test that ValueError is handled with exit code 1."""

        @click.command()
        @handle_errors
        def test_cmd():
            raise ValueError("Invalid input")

        runner = CliRunner()
        result = runner.invoke(test_cmd)
        assert result.exit_code == 1
        assert "Invalid value" in result.output

    def test_handle_errors_keyboard_interrupt(self):
        """Test that KeyboardInterrupt is handled with exit code 1."""

        @click.command()
        @handle_errors
        def test_cmd():
            raise KeyboardInterrupt()

        runner = CliRunner()
        result = runner.invoke(test_cmd)
        assert result.exit_code == 1
        assert "Interrupted" in result.output

    def test_handle_errors_click_abort(self):
        """Test that click.Abort is handled with exit code 1."""

        @click.command()
        @handle_errors
        def test_cmd():
            raise click.Abort()

        runner = CliRunner()
        result = runner.invoke(test_cmd)
        assert result.exit_code == 1
        assert "Cancelled" in result.output

    def test_handle_errors_unexpected_exception(self):
        """Test that unexpected exceptions are handled with exit code 2."""

        @click.command()
        @handle_errors
        def test_cmd():
            raise RuntimeError("Unexpected error")

        runner = CliRunner()
        result = runner.invoke(test_cmd)
        assert result.exit_code == 2
        assert "Unexpected error" in result.output

    def test_handle_errors_verbose_traceback(self):
        """Test that verbose flag shows traceback."""

        @click.command()
        @common_options
        @handle_errors
        def test_cmd(verbose, yes, dry_run, json_output):
            raise RuntimeError("Test error")

        runner = CliRunner()
        result = runner.invoke(test_cmd, ["--verbose"])
        assert result.exit_code == 2
        assert "Full traceback" in result.output
