"""Tests for shell detection and command generation utilities."""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from prime_uve.utils.shell import (
    detect_shell,
    escape_shell_value,
    generate_activation_command,
    generate_export_command,
    get_activation_script,
)


class TestDetectShell:
    """Tests for shell detection."""

    def test_detect_bash_from_shell_env(self, monkeypatch):
        """Test detecting bash from SHELL environment variable."""
        monkeypatch.setenv("SHELL", "/bin/bash")
        assert detect_shell() == "bash"

    def test_detect_zsh_from_shell_env(self, monkeypatch):
        """Test detecting zsh from SHELL environment variable."""
        monkeypatch.setenv("SHELL", "/usr/bin/zsh")
        assert detect_shell() == "zsh"

    def test_detect_fish_from_shell_env(self, monkeypatch):
        """Test detecting fish from SHELL environment variable."""
        monkeypatch.setenv("SHELL", "/usr/local/bin/fish")
        assert detect_shell() == "fish"

    def test_detect_powershell_on_windows(self, monkeypatch):
        """Test detecting PowerShell on Windows via PSModulePath."""
        monkeypatch.delenv("SHELL", raising=False)
        monkeypatch.setenv("PSModulePath", "C:\\Program Files\\PowerShell\\Modules")

        with patch.object(sys, "platform", "win32"):
            assert detect_shell() == "pwsh"

    def test_detect_cmd_on_windows(self, monkeypatch):
        """Test detecting cmd on Windows as fallback."""
        monkeypatch.delenv("SHELL", raising=False)
        monkeypatch.delenv("PSModulePath", raising=False)

        with patch.object(sys, "platform", "win32"):
            assert detect_shell() == "cmd"

    def test_default_fallback_to_bash(self, monkeypatch):
        """Test fallback to bash when shell cannot be detected."""
        monkeypatch.delenv("SHELL", raising=False)
        monkeypatch.delenv("PSModulePath", raising=False)

        with patch.object(sys, "platform", "linux"):
            assert detect_shell() == "bash"


class TestGetActivationScript:
    """Tests for activation script path generation."""

    def test_bash_activation_script(self, tmp_path):
        """Test bash uses bin/activate."""
        venv_path = tmp_path / "venv"
        script = get_activation_script("bash", venv_path)
        assert script == venv_path / "bin" / "activate"

    def test_zsh_activation_script(self, tmp_path):
        """Test zsh uses bin/activate."""
        venv_path = tmp_path / "venv"
        script = get_activation_script("zsh", venv_path)
        assert script == venv_path / "bin" / "activate"

    def test_fish_activation_script(self, tmp_path):
        """Test fish uses bin/activate.fish."""
        venv_path = tmp_path / "venv"
        script = get_activation_script("fish", venv_path)
        assert script == venv_path / "bin" / "activate.fish"

    def test_powershell_activation_script(self, tmp_path):
        """Test PowerShell uses Scripts/Activate.ps1."""
        venv_path = tmp_path / "venv"
        script = get_activation_script("pwsh", venv_path)
        assert script == venv_path / "Scripts" / "Activate.ps1"

    def test_cmd_activation_script(self, tmp_path):
        """Test cmd uses Scripts/activate.bat."""
        venv_path = tmp_path / "venv"
        script = get_activation_script("cmd", venv_path)
        assert script == venv_path / "Scripts" / "activate.bat"

    def test_unknown_shell_falls_back_to_bash(self, tmp_path):
        """Test unknown shell falls back to bash activation."""
        venv_path = tmp_path / "venv"
        script = get_activation_script("unknown-shell", venv_path)
        assert script == venv_path / "bin" / "activate"


class TestEscapeShellValue:
    """Tests for escaping special characters in shell values."""

    def test_escape_bash_double_quotes(self):
        """Test escaping double quotes in bash."""
        value = 'test "value" here'
        escaped = escape_shell_value(value, "bash")
        assert '\\"' in escaped

    def test_escape_bash_backslashes(self):
        """Test escaping backslashes in bash."""
        value = r"test\value\here"
        escaped = escape_shell_value(value, "bash")
        assert "\\\\" in escaped

    def test_bash_preserves_variable_syntax(self):
        """Test that ${VAR} syntax is preserved in bash."""
        value = "${HOME}/path/to/dir"
        escaped = escape_shell_value(value, "bash")
        # Should not escape the $ in ${HOME}
        assert "${HOME}" in escaped

    def test_escape_powershell_double_quotes(self):
        """Test escaping double quotes in PowerShell."""
        value = 'test "value" here'
        escaped = escape_shell_value(value, "pwsh")
        assert '`"' in escaped

    def test_escape_cmd_minimal(self):
        """Test cmd has minimal escaping."""
        value = 'test "value" here'
        escaped = escape_shell_value(value, "cmd")
        # CMD doesn't escape much
        assert escaped == value


class TestGenerateExportCommand:
    """Tests for generating shell-specific export commands."""

    def test_bash_export_command(self):
        """Test bash export syntax."""
        cmd = generate_export_command("bash", "MY_VAR", "value123")
        assert cmd == 'export MY_VAR="value123"'

    def test_zsh_export_command(self):
        """Test zsh export syntax."""
        cmd = generate_export_command("zsh", "MY_VAR", "value123")
        assert cmd == 'export MY_VAR="value123"'

    def test_fish_export_command(self):
        """Test fish export syntax."""
        cmd = generate_export_command("fish", "MY_VAR", "value123")
        assert cmd == 'set -x MY_VAR "value123"'

    def test_powershell_export_command(self):
        """Test PowerShell export syntax."""
        cmd = generate_export_command("pwsh", "MY_VAR", "value123")
        assert cmd == '$env:MY_VAR="value123"'

    def test_cmd_export_command(self):
        """Test cmd export syntax."""
        cmd = generate_export_command("cmd", "MY_VAR", "value123")
        assert cmd == "set MY_VAR=value123"

    def test_cmd_replaces_home_variable(self):
        """Test that cmd replaces ${HOME} with %HOME%."""
        cmd = generate_export_command("cmd", "MY_VAR", "${HOME}/path")
        assert "%HOME%" in cmd
        assert "${HOME}" not in cmd

    def test_bash_preserves_variable_syntax(self):
        """Test that bash preserves ${VAR} syntax."""
        cmd = generate_export_command("bash", "UV_PROJECT_ENVIRONMENT", "${HOME}/venvs/test")
        assert "${HOME}" in cmd
        assert 'export UV_PROJECT_ENVIRONMENT="${HOME}/venvs/test"' == cmd

    def test_export_with_special_characters(self):
        """Test exporting values with special characters."""
        cmd = generate_export_command("bash", "DB_URL", "postgresql://user:pass@localhost/db")
        assert 'export DB_URL="postgresql://user:pass@localhost/db"' in cmd

    def test_unknown_shell_falls_back_to_bash(self):
        """Test unknown shell uses bash syntax."""
        cmd = generate_export_command("unknown-shell", "MY_VAR", "value")
        assert cmd == 'export MY_VAR="value"'


class TestGenerateActivationCommand:
    """Tests for generating shell-specific activation commands."""

    def test_bash_activation_command(self, tmp_path):
        """Test bash activation command."""
        venv_path = tmp_path / "venv"
        cmd = generate_activation_command("bash", venv_path)
        assert cmd == f"source {venv_path / 'bin' / 'activate'}"

    def test_zsh_activation_command(self, tmp_path):
        """Test zsh activation command."""
        venv_path = tmp_path / "venv"
        cmd = generate_activation_command("zsh", venv_path)
        assert cmd == f"source {venv_path / 'bin' / 'activate'}"

    def test_fish_activation_command(self, tmp_path):
        """Test fish activation command."""
        venv_path = tmp_path / "venv"
        cmd = generate_activation_command("fish", venv_path)
        assert cmd == f"source {venv_path / 'bin' / 'activate.fish'}"

    def test_powershell_activation_command(self, tmp_path):
        """Test PowerShell activation command."""
        venv_path = tmp_path / "venv"
        cmd = generate_activation_command("pwsh", venv_path)
        assert cmd == f"& {venv_path / 'Scripts' / 'Activate.ps1'}"

    def test_cmd_activation_command(self, tmp_path):
        """Test cmd activation command."""
        venv_path = tmp_path / "venv"
        cmd = generate_activation_command("cmd", venv_path)
        assert cmd == f"call {venv_path / 'Scripts' / 'activate.bat'}"

    def test_unknown_shell_falls_back_to_bash(self, tmp_path):
        """Test unknown shell uses bash activation."""
        venv_path = tmp_path / "venv"
        cmd = generate_activation_command("unknown-shell", venv_path)
        assert cmd == f"source {venv_path / 'bin' / 'activate'}"
