"""Tests for prime-uve configure vscode command."""

import json
import sys

import pytest
from click.testing import CliRunner

from prime_uve.cli.main import cli


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_project(tmp_path):
    """Create a mock Python project with initialized venv."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create pyproject.toml
    pyproject = project_dir / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-project"\nversion = "0.1.0"\n')

    # Create .env.uve with venv path (no quotes)
    venv_dir = tmp_path / "venvs" / "test_venv"
    env_file = project_dir / ".env.uve"
    env_file.write_text(f"UV_PROJECT_ENVIRONMENT={venv_dir}\n")

    # Create venv directory with Python interpreter
    venv_dir.mkdir(parents=True)
    if sys.platform == "win32":
        interpreter = venv_dir / "Scripts" / "python.exe"
    else:
        interpreter = venv_dir / "bin" / "python"
    interpreter.parent.mkdir(parents=True, exist_ok=True)
    interpreter.write_text("")  # Create empty file

    return project_dir


# Basic Functionality Tests


def test_configure_vscode_creates_workspace(runner, mock_project, monkeypatch):
    """Test that configure vscode creates workspace file when none exists."""
    monkeypatch.chdir(mock_project)

    result = runner.invoke(cli, ["configure", "vscode", "--yes"])

    assert result.exit_code == 0, f"Failed with: {result.output}"

    # Check workspace created
    workspace = mock_project / f"{mock_project.name}.code-workspace"
    assert workspace.exists()

    # Check content
    data = json.loads(workspace.read_text())
    assert "folders" in data
    assert "settings" in data
    assert "python.defaultInterpreterPath" in data["settings"]


def test_configure_vscode_updates_existing_workspace(runner, mock_project, monkeypatch):
    """Test that configure vscode updates existing workspace file."""
    monkeypatch.chdir(mock_project)

    # Create existing workspace
    workspace = mock_project / "test.code-workspace"
    workspace.write_text(
        json.dumps(
            {
                "folders": [{"path": "."}],
                "settings": {
                    "python.defaultInterpreterPath": "/old/path",
                    "editor.fontSize": 14,
                },
            }
        )
    )

    result = runner.invoke(cli, ["configure", "vscode", "--yes"])

    assert result.exit_code == 0

    # Check workspace updated
    data = json.loads(workspace.read_text())
    assert "python.defaultInterpreterPath" in data["settings"]
    # Should preserve other settings
    assert data["settings"]["editor.fontSize"] == 14


def test_configure_vscode_sets_correct_interpreter(
    runner, mock_project, monkeypatch, tmp_path
):
    """Test that configure vscode sets correct interpreter path."""
    monkeypatch.chdir(mock_project)

    result = runner.invoke(cli, ["configure", "vscode", "--yes"])

    assert result.exit_code == 0

    workspace = mock_project / f"{mock_project.name}.code-workspace"
    data = json.loads(workspace.read_text())

    interpreter_path = data["settings"]["python.defaultInterpreterPath"]
    if sys.platform == "win32":
        assert "Scripts" in interpreter_path
        assert interpreter_path.endswith("python.exe")
    else:
        assert "/bin/python" in interpreter_path


def test_configure_vscode_preserves_other_settings(runner, mock_project, monkeypatch):
    """Test that other workspace settings are preserved."""
    monkeypatch.chdir(mock_project)

    # Create workspace with various settings
    workspace = mock_project / "test.code-workspace"
    original_data = {
        "folders": [{"path": "."}, {"path": "../other"}],
        "settings": {
            "python.defaultInterpreterPath": "/old/path",
            "editor.fontSize": 14,
            "python.linting.enabled": True,
            "terminal.integrated.shell.linux": "/bin/bash",
        },
        "extensions": {"recommendations": ["ms-python.python"]},
    }
    workspace.write_text(json.dumps(original_data))

    result = runner.invoke(cli, ["configure", "vscode", "--yes"])

    assert result.exit_code == 0

    # Check all original settings preserved except interpreter
    data = json.loads(workspace.read_text())
    assert data["folders"] == original_data["folders"]
    assert data["settings"]["editor.fontSize"] == 14
    assert data["settings"]["python.linting.enabled"] is True
    assert data["extensions"] == original_data["extensions"]


def test_configure_vscode_shows_success_message(runner, mock_project, monkeypatch):
    """Test that success message is shown."""
    monkeypatch.chdir(mock_project)

    result = runner.invoke(cli, ["configure", "vscode", "--yes"])

    assert result.exit_code == 0
    assert "Python interpreter set to venv" in result.output or "OK" in result.output


# Multiple Workspace Files Tests


def test_configure_vscode_multiple_files_prompts_user(
    runner, mock_project, monkeypatch
):
    """Test that multiple workspace files prompt user to choose."""
    monkeypatch.chdir(mock_project)

    # Create multiple workspace files
    workspace1 = mock_project / "test1.code-workspace"
    workspace1.write_text('{"folders": []}')

    vscode_dir = mock_project / ".vscode"
    vscode_dir.mkdir()
    workspace2 = vscode_dir / "test2.code-workspace"
    workspace2.write_text('{"folders": []}')

    # Provide choice via input
    result = runner.invoke(cli, ["configure", "vscode", "--yes"], input="1\n")

    assert result.exit_code == 0
    assert "Multiple workspace files found" in result.output


def test_configure_vscode_multiple_files_user_selects(
    runner, mock_project, monkeypatch
):
    """Test user can select specific workspace file."""
    monkeypatch.chdir(mock_project)

    # Create multiple workspace files
    workspace1 = mock_project / "test1.code-workspace"
    workspace1.write_text('{"folders": []}')

    workspace2 = mock_project / "test2.code-workspace"
    workspace2.write_text('{"folders": []}')

    # Select second file
    result = runner.invoke(cli, ["configure", "vscode", "--yes"], input="2\n")

    assert result.exit_code == 0

    # Check second workspace was updated
    data = json.loads(workspace2.read_text())
    assert "python.defaultInterpreterPath" in data.get("settings", {})


def test_configure_vscode_workspace_option(runner, mock_project, monkeypatch):
    """Test --workspace option specifies file directly."""
    monkeypatch.chdir(mock_project)

    # Create multiple workspace files
    workspace1 = mock_project / "test1.code-workspace"
    workspace1.write_text('{"folders": []}')

    workspace2 = mock_project / "test2.code-workspace"
    workspace2.write_text('{"folders": []}')

    # Use --workspace to specify which one
    result = runner.invoke(
        cli, ["configure", "vscode", "--workspace", "test2.code-workspace", "--yes"]
    )

    assert result.exit_code == 0

    # Check second workspace was updated
    data = json.loads(workspace2.read_text())
    assert "python.defaultInterpreterPath" in data.get("settings", {})


# Edge Cases


def test_configure_vscode_not_initialized(runner, tmp_path, monkeypatch):
    """Test error when project not initialized."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create pyproject.toml but no .env.uve
    pyproject = project_dir / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test"\n')

    monkeypatch.chdir(project_dir)

    result = runner.invoke(cli, ["configure", "vscode"])

    assert result.exit_code != 0
    assert "not initialized" in result.output.lower() or "No .env.uve" in result.output


def test_configure_vscode_venv_not_found(runner, mock_project, monkeypatch):
    """Test error when venv doesn't exist."""
    monkeypatch.chdir(mock_project)

    # Update .env.uve to point to non-existent venv
    env_file = mock_project / ".env.uve"
    env_file.write_text('UV_PROJECT_ENVIRONMENT="/nonexistent/venv"\n')

    result = runner.invoke(cli, ["configure", "vscode"])

    assert result.exit_code != 0
    assert "not found" in result.output.lower() or "Venv not found" in result.output


def test_configure_vscode_malformed_workspace(runner, mock_project, monkeypatch):
    """Test handling of malformed workspace JSON."""
    monkeypatch.chdir(mock_project)

    # Create malformed workspace
    workspace = mock_project / "test.code-workspace"
    workspace.write_text("{ invalid json }")

    # Should prompt for backup and recreate
    result = runner.invoke(cli, ["configure", "vscode", "--yes"])

    assert result.exit_code == 0

    # Check backup created
    backup = mock_project / "test.code-workspace.bak"
    assert backup.exists()

    # Check new workspace is valid
    data = json.loads(workspace.read_text())
    assert "settings" in data


def test_configure_vscode_empty_workspace(runner, mock_project, monkeypatch):
    """Test handling of empty workspace file."""
    monkeypatch.chdir(mock_project)

    # Create minimal workspace
    workspace = mock_project / "test.code-workspace"
    workspace.write_text("{}")

    result = runner.invoke(cli, ["configure", "vscode", "--yes"])

    assert result.exit_code == 0

    # Check settings added
    data = json.loads(workspace.read_text())
    assert "settings" in data
    assert "python.defaultInterpreterPath" in data["settings"]


# Confirmation and Safety Tests


def test_configure_vscode_confirmation_when_overwriting(
    runner, mock_project, monkeypatch
):
    """Test confirmation prompt when existing interpreter is set."""
    monkeypatch.chdir(mock_project)

    # Create workspace with existing interpreter
    workspace = mock_project / "test.code-workspace"
    workspace.write_text(
        json.dumps(
            {
                "folders": [{"path": "."}],
                "settings": {"python.defaultInterpreterPath": "/old/path"},
            }
        )
    )

    # Without --yes, should prompt
    result = runner.invoke(cli, ["configure", "vscode"], input="y\n")

    assert result.exit_code == 0
    assert (
        "Update workspace?" in result.output or "Current interpreter" in result.output
    )


def test_configure_vscode_yes_skips_confirmation(runner, mock_project, monkeypatch):
    """Test --yes skips confirmation prompts."""
    monkeypatch.chdir(mock_project)

    # Create workspace with existing interpreter
    workspace = mock_project / "test.code-workspace"
    workspace.write_text(
        json.dumps(
            {
                "folders": [{"path": "."}],
                "settings": {"python.defaultInterpreterPath": "/old/path"},
            }
        )
    )

    # With --yes, should not prompt
    result = runner.invoke(cli, ["configure", "vscode", "--yes"])

    assert result.exit_code == 0


def test_configure_vscode_dry_run(runner, mock_project, monkeypatch):
    """Test --dry-run shows changes without applying."""
    monkeypatch.chdir(mock_project)

    # Create workspace
    workspace = mock_project / "test.code-workspace"
    original_data = {
        "folders": [{"path": "."}],
        "settings": {"python.defaultInterpreterPath": "/old/path"},
    }
    workspace.write_text(json.dumps(original_data))

    result = runner.invoke(cli, ["configure", "vscode", "--dry-run", "--yes"])

    assert result.exit_code == 0, f"Failed with: {result.output}"
    assert "[DRY RUN]" in result.output
    assert "Would update" in result.output

    # Check workspace not modified
    data = json.loads(workspace.read_text())
    assert data == original_data


# Options Tests


def test_configure_vscode_create_flag(runner, mock_project, monkeypatch):
    """Test --create forces new workspace creation."""
    monkeypatch.chdir(mock_project)

    result = runner.invoke(cli, ["configure", "vscode", "--create", "--yes"])

    assert result.exit_code == 0

    # Check workspace created
    workspace = mock_project / f"{mock_project.name}.code-workspace"
    assert workspace.exists()


def test_configure_vscode_verbose(runner, mock_project, monkeypatch):
    """Test verbose mode shows details."""
    monkeypatch.chdir(mock_project)

    result = runner.invoke(cli, ["configure", "vscode", "--verbose", "--yes"])

    assert result.exit_code == 0
    assert "Workspace:" in result.output or "Interpreter:" in result.output


def test_configure_vscode_json_output(runner, mock_project, monkeypatch):
    """Test JSON output mode."""
    monkeypatch.chdir(mock_project)

    result = runner.invoke(cli, ["configure", "vscode", "--json", "--yes"])

    assert result.exit_code == 0, f"Failed with: {result.output}"

    # Find JSON in output - it may span multiple lines
    # Look for the start of JSON object and parse from there
    output = result.output
    json_start = output.find("{")
    if json_start >= 0:
        # Find the matching closing brace (simple approach for nested objects)
        json_text = output[json_start:]
        # Try to parse - if it fails, the JSON might be incomplete
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            # Try extracting just the JSON block by finding balanced braces
            brace_count = 0
            json_end = json_start
            for i, char in enumerate(output[json_start:], json_start):
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break
            json_text = output[json_start:json_end]
            data = json.loads(json_text)

        assert "workspace_file" in data
        assert "interpreter_path" in data
    else:
        # No JSON found
        assert False, f"No JSON found in output: {output}"


# No Project Root Tests


def test_configure_vscode_no_pyproject(runner, tmp_path, monkeypatch):
    """Test error when not in a Python project."""
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(cli, ["configure", "vscode"])

    assert result.exit_code != 0
    assert (
        "Not in a Python project" in result.output or "pyproject.toml" in result.output
    )


# Workspace with Comments Tests


def test_configure_vscode_preserves_workspace_with_comments(
    runner, mock_project, monkeypatch
):
    """Test that workspace files with comments are handled correctly."""
    monkeypatch.chdir(mock_project)

    # Create workspace with comments
    workspace = mock_project / "test.code-workspace"
    content = """{
    // Workspace configuration
    "folders": [
        {"path": "."}  // Root folder
    ],
    "settings": {
        // Python settings
        "python.defaultInterpreterPath": "/old/path"
    }
}"""
    workspace.write_text(content)

    result = runner.invoke(cli, ["configure", "vscode", "--yes"])

    assert result.exit_code == 0

    # Check workspace is valid (comments removed during read/write)
    data = json.loads(workspace.read_text())
    assert "settings" in data
    assert "python.defaultInterpreterPath" in data["settings"]
