"""Shell detection and command generation utilities for venv activation."""

import os
import sys
from pathlib import Path


def detect_shell() -> str:
    """Detect current shell from environment variables.

    Returns:
        Shell name: bash, zsh, fish, pwsh, or cmd
    """
    # Check SHELL env var (Unix)
    shell_path = os.environ.get("SHELL", "")
    if shell_path:
        shell_name = os.path.basename(shell_path)
        if "bash" in shell_name:
            return "bash"
        elif "zsh" in shell_name:
            return "zsh"
        elif "fish" in shell_name:
            return "fish"

    # Windows detection
    if sys.platform == "win32":
        # Check if running in PowerShell
        if os.environ.get("PSModulePath"):
            return "pwsh"
        # Fallback to cmd
        return "cmd"

    # Default fallback
    return "bash"


def get_activation_script(shell: str, venv_path: Path) -> Path:
    """Get path to activation script for given shell.

    Args:
        shell: Shell type (bash, zsh, fish, pwsh, cmd)
        venv_path: Path to virtual environment (expanded)

    Returns:
        Path to activation script
    """
    if shell in ("bash", "zsh"):
        return venv_path / "bin" / "activate"
    elif shell == "fish":
        return venv_path / "bin" / "activate.fish"
    elif shell in ("pwsh", "powershell"):
        return venv_path / "Scripts" / "Activate.ps1"
    elif shell == "cmd":
        return venv_path / "Scripts" / "activate.bat"
    else:
        # Fallback to bash
        return venv_path / "bin" / "activate"


def escape_shell_value(value: str, shell: str) -> str:
    """Escape special characters in value for shell.

    Args:
        value: Variable value to escape
        shell: Shell type

    Returns:
        Escaped value
    """
    if shell in ("bash", "zsh", "fish"):
        # Escape backslashes, double quotes, and dollar signs
        # Note: We need to preserve variable syntax like ${HOME}
        # So we escape literal $ but not ${ } patterns
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        # Don't escape $ in ${VAR} patterns, only standalone $
        # This is tricky - for now, don't escape $ at all since we want
        # variables like ${HOME} to remain unexpanded in the export
        return escaped
    elif shell in ("pwsh", "powershell"):
        # Escape double quotes with backtick
        return value.replace('"', '`"')
    elif shell == "cmd":
        # CMD has minimal escaping needs
        return value
    return value


def generate_export_command(shell: str, var_name: str, var_value: str) -> str:
    """Generate shell-specific export command.

    IMPORTANT: Keep variables unexpanded (e.g., ${HOME} stays as ${HOME}).
    Only the activation script path gets expanded.

    Args:
        shell: Shell type
        var_name: Variable name
        var_value: Variable value (unexpanded form with ${VAR} syntax)

    Returns:
        Shell-specific export command
    """
    # Escape special characters in value
    value_escaped = escape_shell_value(var_value, shell)

    if shell in ("bash", "zsh"):
        return f'export {var_name}="{value_escaped}"'
    elif shell == "fish":
        return f'set -x {var_name} "{value_escaped}"'
    elif shell in ("pwsh", "powershell"):
        return f'$env:{var_name}="{value_escaped}"'
    elif shell == "cmd":
        # CMD uses % for variables, not $
        # Replace ${HOME} with %HOME%
        value_cmd = value_escaped.replace("${HOME}", "%HOME%").replace(
            "$HOME", "%HOME%"
        )
        return f"set {var_name}={value_cmd}"
    else:
        # Fallback to bash syntax
        return f'export {var_name}="{value_escaped}"'


def generate_activation_command(shell: str, venv_path: Path) -> str:
    """Generate shell-specific venv activation command.

    venv_path is the EXPANDED path (variables already resolved).

    Args:
        shell: Shell type
        venv_path: Expanded path to virtual environment

    Returns:
        Shell-specific activation command
    """
    activate_script = get_activation_script(shell, venv_path)

    if shell in ("bash", "zsh"):
        return f"source {activate_script}"
    elif shell == "fish":
        return f"source {activate_script}"
    elif shell in ("pwsh", "powershell"):
        # Use & operator for PowerShell
        return f"& {activate_script}"
    elif shell == "cmd":
        return f"call {activate_script}"
    else:
        # Fallback to bash
        return f"source {activate_script}"
