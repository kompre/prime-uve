"""Tests for VS Code workspace utilities."""

import json
from pathlib import Path

import pytest

from prime_uve.utils.vscode import (
    absolute_to_vscode_path,
    create_default_workspace,
    find_workspace_files,
    get_platform_suffix,
    get_workspace_filename,
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


# Platform Suffix Tests


def test_get_platform_suffix(monkeypatch):
    """Test platform name mapping."""
    import platform as platform_mod

    # Test Linux
    monkeypatch.setattr(platform_mod, "system", lambda: "Linux")
    assert get_platform_suffix() == "linux"

    # Test macOS
    monkeypatch.setattr(platform_mod, "system", lambda: "Darwin")
    assert get_platform_suffix() == "macos"

    # Test Windows
    monkeypatch.setattr(platform_mod, "system", lambda: "Windows")
    assert get_platform_suffix() == "windows"


def test_get_platform_suffix_unknown(monkeypatch):
    """Test unknown platform fallback."""
    import platform as platform_mod

    monkeypatch.setattr(platform_mod, "system", lambda: "FreeBSD")
    assert get_platform_suffix() == "freebsd"  # Lowercased


# Path Translation Tests


def test_absolute_to_vscode_path_linux(monkeypatch):
    """Test path translation on Linux."""
    import platform as platform_mod
    import os

    monkeypatch.setattr(platform_mod, "system", lambda: "Linux")
    monkeypatch.setattr(os.path, "expanduser", lambda x: "/home/testuser")

    # Test home directory replacement
    path = Path("/home/testuser/.cache/prime-uve/venvs/project_abc123")
    result = absolute_to_vscode_path(path)

    assert result == "${env:HOME}/.cache/prime-uve/venvs/project_abc123"


def test_absolute_to_vscode_path_macos(monkeypatch):
    """Test path translation on macOS."""
    import platform as platform_mod
    import os

    monkeypatch.setattr(platform_mod, "system", lambda: "Darwin")
    monkeypatch.setattr(os.path, "expanduser", lambda x: "/Users/testuser")

    # Test home directory replacement
    path = Path("/Users/testuser/Library/Caches/prime-uve/venvs/project_abc123")
    result = absolute_to_vscode_path(path)

    assert result == "${env:HOME}/Library/Caches/prime-uve/venvs/project_abc123"


def test_absolute_to_vscode_path_windows(monkeypatch):
    """Test path translation on Windows."""
    import platform as platform_mod

    monkeypatch.setattr(platform_mod, "system", lambda: "Windows")
    monkeypatch.setenv("LOCALAPPDATA", "C:\\Users\\testuser\\AppData\\Local")

    # Test LOCALAPPDATA replacement
    path = Path("C:/Users/testuser/AppData/Local/prime-uve/Cache/venvs/project_abc123")
    result = absolute_to_vscode_path(path)

    assert result == "${env:LOCALAPPDATA}/prime-uve/Cache/venvs/project_abc123"


def test_absolute_to_vscode_path_linux_xdg(monkeypatch):
    """Test XDG_CACHE_HOME on Linux."""
    import platform as platform_mod

    monkeypatch.setattr(platform_mod, "system", lambda: "Linux")
    monkeypatch.setenv("XDG_CACHE_HOME", "/custom/cache")

    # Test XDG_CACHE_HOME replacement
    path = Path("/custom/cache/prime-uve/venvs/project_abc123")
    result = absolute_to_vscode_path(path)

    assert result == "${env:XDG_CACHE_HOME}/prime-uve/venvs/project_abc123"


def test_absolute_to_vscode_path_fallback():
    """Test fallback to absolute path when no variables match."""

    # Test with custom path that doesn't match any variables
    path = Path("/opt/custom/venv/project")
    result = absolute_to_vscode_path(path)

    # Should return absolute path with forward slashes
    assert result == "/opt/custom/venv/project"


# Workspace Filename Tests


def test_get_workspace_filename_no_suffix(tmp_path):
    """Test workspace filename without suffix."""
    project_root = tmp_path / "myproject"
    project_root.mkdir()

    result = get_workspace_filename(project_root, None, None)

    assert result == project_root / "myproject.code-workspace"


def test_get_workspace_filename_with_suffix(tmp_path):
    """Test workspace filename with suffix."""
    project_root = tmp_path / "myproject"
    project_root.mkdir()

    result = get_workspace_filename(project_root, "linux", None)

    assert result == project_root / "myproject.linux.code-workspace"


def test_get_workspace_filename_based_on_existing(tmp_path):
    """Test workspace filename based on existing file."""
    project_root = tmp_path / "myproject"
    project_root.mkdir()

    existing = project_root / "custom.code-workspace"
    existing.touch()

    result = get_workspace_filename(project_root, "dev", existing)

    assert result == project_root / "custom.dev.code-workspace"


def test_get_workspace_filename_strips_platform_suffix(tmp_path):
    """Test that existing platform suffixes are stripped."""
    project_root = tmp_path / "myproject"
    project_root.mkdir()

    existing = project_root / "custom.linux.code-workspace"
    existing.touch()

    result = get_workspace_filename(project_root, "macos", existing)

    # Should strip .linux and add .macos
    assert result == project_root / "custom.macos.code-workspace"


def test_get_workspace_filename_multiple_dots(tmp_path):
    """Test workspace filename with multiple dots in name."""
    project_root = tmp_path / "my.cool.project"
    project_root.mkdir()

    result = get_workspace_filename(project_root, "windows", None)

    assert result == project_root / "my.cool.project.windows.code-workspace"
