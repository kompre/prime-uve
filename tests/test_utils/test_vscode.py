"""Tests for VS Code workspace utilities."""

import json
from pathlib import Path

import pytest

from prime_uve.utils.vscode import (
    create_default_workspace,
    find_workspace_files,
    read_workspace,
    strip_json_comments,
    update_workspace_settings,
    write_workspace,
)


# Workspace Discovery Tests


def test_find_workspace_files_single(tmp_path):
    """Test finding a single workspace file in project root."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    workspace = project_root / "test.code-workspace"
    workspace.write_text('{"folders": []}')

    result = find_workspace_files(project_root)

    assert len(result) == 1
    assert result[0] == workspace


def test_find_workspace_files_multiple(tmp_path):
    """Test finding multiple workspace files."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    # Create workspace in root
    workspace1 = project_root / "test1.code-workspace"
    workspace1.write_text('{"folders": []}')

    # Create workspace in .vscode
    vscode_dir = project_root / ".vscode"
    vscode_dir.mkdir()
    workspace2 = vscode_dir / "test2.code-workspace"
    workspace2.write_text('{"folders": []}')

    result = find_workspace_files(project_root)

    assert len(result) == 2
    assert workspace1 in result
    assert workspace2 in result


def test_find_workspace_files_none(tmp_path):
    """Test when no workspace files exist."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    result = find_workspace_files(project_root)

    assert len(result) == 0


def test_find_workspace_files_only_in_vscode(tmp_path):
    """Test finding workspace only in .vscode directory."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    vscode_dir = project_root / ".vscode"
    vscode_dir.mkdir()
    workspace = vscode_dir / "workspace.code-workspace"
    workspace.write_text('{"folders": []}')

    result = find_workspace_files(project_root)

    assert len(result) == 1
    assert result[0] == workspace


# JSON Comment Stripping Tests


def test_strip_json_comments_line_comments():
    """Test removing // style comments."""
    content = """{
    "key": "value",  // This is a comment
    "other": "data"  // Another comment
}"""

    result = strip_json_comments(content)

    assert "//" not in result
    assert "value" in result
    assert "data" in result


def test_strip_json_comments_block_comments():
    """Test removing /* */ style comments."""
    content = """{
    /* This is a block comment */
    "key": "value",
    /* Multi-line
       block comment */
    "other": "data"
}"""

    result = strip_json_comments(content)

    assert "/*" not in result
    assert "*/" not in result
    assert "value" in result
    assert "data" in result


def test_strip_json_comments_mixed():
    """Test removing both comment styles."""
    content = """{
    // Line comment
    "key": "value",  // Inline comment
    /* Block comment */
    "other": "data"
}"""

    result = strip_json_comments(content)

    assert "//" not in result
    assert "/*" not in result
    assert "value" in result
    assert "data" in result


def test_strip_json_comments_preserves_strings():
    """Test that // and /* */ inside strings are preserved."""
    content = """{
    "url": "http://example.com",
    "comment": "This /* is */ not a comment"
}"""

    result = strip_json_comments(content)

    assert "http://example.com" in result
    assert "This /* is */ not a comment" in result


# JSON Read/Write Tests


def test_read_workspace_valid(tmp_path):
    """Test reading a valid workspace file."""
    workspace = tmp_path / "test.code-workspace"
    data = {
        "folders": [{"path": "."}],
        "settings": {"python.defaultInterpreterPath": "/path/to/python"},
    }
    workspace.write_text(json.dumps(data, indent=2))

    result = read_workspace(workspace)

    assert result == data


def test_read_workspace_with_comments(tmp_path):
    """Test reading workspace file with comments."""
    workspace = tmp_path / "test.code-workspace"
    content = """{
    // Workspace configuration
    "folders": [
        {"path": "."}  // Root folder
    ],
    "settings": {
        "python.defaultInterpreterPath": "/path/to/python"
    }
}"""
    workspace.write_text(content)

    result = read_workspace(workspace)

    assert "folders" in result
    assert "settings" in result
    assert result["settings"]["python.defaultInterpreterPath"] == "/path/to/python"


def test_read_workspace_malformed(tmp_path):
    """Test reading malformed JSON raises ValueError."""
    workspace = tmp_path / "test.code-workspace"
    workspace.write_text("{ invalid json }")

    with pytest.raises(ValueError, match="Malformed workspace file"):
        read_workspace(workspace)


def test_write_workspace(tmp_path):
    """Test writing workspace file."""
    workspace = tmp_path / "test.code-workspace"
    data = {
        "folders": [{"path": "."}],
        "settings": {"python.defaultInterpreterPath": "/path/to/python"},
    }

    write_workspace(workspace, data)

    assert workspace.exists()
    content = workspace.read_text()
    assert "folders" in content
    assert "python.defaultInterpreterPath" in content
    # Check trailing newline
    assert content.endswith("\n")


def test_write_workspace_preserves_unicode(tmp_path):
    """Test that write_workspace preserves unicode characters."""
    workspace = tmp_path / "test.code-workspace"
    data = {
        "folders": [{"path": "."}],
        "settings": {"description": "Test with unicode: \u2713"},
    }

    write_workspace(workspace, data)

    content = workspace.read_text(encoding="utf-8")
    assert "\u2713" in content or "✓" in content


# Setting Update Tests


def test_update_workspace_settings_new():
    """Test adding all Python settings to empty workspace."""
    workspace = {"folders": [{"path": "."}]}
    interpreter_path = Path("/path/to/venv/bin/python")

    result = update_workspace_settings(workspace, interpreter_path)

    assert "settings" in result
    assert result["settings"]["python.defaultInterpreterPath"] == str(interpreter_path)
    assert result["settings"]["python.terminal.activateEnvironment"] is True
    assert result["settings"]["python.envFile"] == "${workspaceFolder}/.env.uve"


def test_update_workspace_settings_existing():
    """Test updating existing Python settings."""
    workspace = {
        "folders": [{"path": "."}],
        "settings": {
            "python.defaultInterpreterPath": "/old/path",
            "python.linting.enabled": True,
        },
    }
    interpreter_path = Path("/new/path/bin/python")

    result = update_workspace_settings(workspace, interpreter_path)

    assert result["settings"]["python.defaultInterpreterPath"] == str(interpreter_path)
    assert result["settings"]["python.terminal.activateEnvironment"] is True
    assert result["settings"]["python.envFile"] == "${workspaceFolder}/.env.uve"
    # Verify other settings preserved
    assert result["settings"]["python.linting.enabled"] is True


def test_update_workspace_settings_preserves_other_settings():
    """Test that updating workspace settings preserves non-Python settings."""
    workspace = {
        "folders": [{"path": "."}],
        "settings": {
            "editor.fontSize": 14,
            "terminal.integrated.shell.linux": "/bin/bash",
        },
    }
    interpreter_path = Path("/path/to/python")

    result = update_workspace_settings(workspace, interpreter_path)

    assert result["settings"]["python.defaultInterpreterPath"] == str(interpreter_path)
    assert result["settings"]["python.terminal.activateEnvironment"] is True
    assert result["settings"]["python.envFile"] == "${workspaceFolder}/.env.uve"
    assert result["settings"]["editor.fontSize"] == 14
    assert result["settings"]["terminal.integrated.shell.linux"] == "/bin/bash"


def test_create_default_workspace():
    """Test creating default workspace structure with all Python settings."""
    project_root = Path("/path/to/project")
    interpreter_path = Path("/path/to/venv/bin/python")

    result = create_default_workspace(project_root, interpreter_path)

    assert "folders" in result
    assert len(result["folders"]) == 1
    assert result["folders"][0]["path"] == "."
    assert "settings" in result
    assert result["settings"]["python.defaultInterpreterPath"] == str(interpreter_path)
    assert result["settings"]["python.terminal.activateEnvironment"] is True
    assert result["settings"]["python.envFile"] == "${workspaceFolder}/.env.uve"


def test_create_default_workspace_complete():
    """Test that default workspace includes all required Python settings."""
    project_root = Path("/path/to/project")
    interpreter_path = Path("/path/to/venv/bin/python")

    result = create_default_workspace(project_root, interpreter_path)

    # Should only have folders and settings
    assert set(result.keys()) == {"folders", "settings"}
    # Settings should have all three Python settings
    assert set(result["settings"].keys()) == {
        "python.defaultInterpreterPath",
        "python.terminal.activateEnvironment",
        "python.envFile",
    }


# Platform-Specific Tests


def test_interpreter_path_format():
    """Test that interpreter paths are strings not Path objects."""
    workspace = {"folders": []}
    interpreter_path = Path("/test/path/to/python")

    result = update_workspace_settings(workspace, interpreter_path)

    # Should be string, not Path object
    assert isinstance(result["settings"]["python.defaultInterpreterPath"], str)
    # Path conversion is platform-specific, just verify it's converted to string
    assert "python" in result["settings"]["python.defaultInterpreterPath"]
