"""Tests for .env.uve file management."""

import os
import stat
import sys
from pathlib import Path

import pytest

from prime_uve.core.env_file import (
    EnvFileError,
    find_env_file,
    find_env_file_strict,
    get_venv_path,
    read_env_file,
    update_env_file,
    write_env_file,
)


# ============================================================================
# Lookup Tests
# ============================================================================


def test_find_env_file_in_current_dir(tmp_path):
    """Finds .env.uve in current directory."""
    env_file = tmp_path / ".env.uve"
    env_file.touch()

    result = find_env_file(tmp_path)
    assert result == env_file


def test_find_env_file_walk_up_to_root(tmp_path):
    """Walks up directory tree to project root."""
    # Create project structure
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "pyproject.toml").touch()
    (project_root / ".env.uve").touch()

    subdir = project_root / "src" / "mypackage"
    subdir.mkdir(parents=True)

    result = find_env_file(subdir)
    assert result == project_root / ".env.uve"


def test_find_env_file_create_at_project_root(tmp_path):
    """Creates .env.uve at project root if missing."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "pyproject.toml").touch()

    subdir = project_root / "src"
    subdir.mkdir()

    result = find_env_file(subdir)
    assert result == project_root / ".env.uve"
    assert result.exists()


def test_find_env_file_create_in_cwd_no_project(tmp_path):
    """Creates .env.uve in cwd if no project root found."""
    some_dir = tmp_path / "some_dir"
    some_dir.mkdir()

    result = find_env_file(some_dir)
    assert result == some_dir / ".env.uve"
    assert result.exists()


def test_find_env_file_stops_at_filesystem_root(tmp_path):
    """Stops walking up at filesystem root."""
    # Create a directory without project root
    some_dir = tmp_path / "some_dir"
    some_dir.mkdir()

    result = find_env_file(some_dir)
    # Should create in the starting directory
    assert result == some_dir / ".env.uve"


def test_find_env_file_custom_start_path(tmp_path):
    """Respects custom start_path parameter."""
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir1.mkdir()
    dir2.mkdir()

    result = find_env_file(dir2)
    assert result == dir2 / ".env.uve"
    assert result.exists()


def test_find_env_file_defaults_to_cwd(tmp_path, monkeypatch):
    """Defaults to current working directory."""
    monkeypatch.chdir(tmp_path)
    result = find_env_file()
    assert result == tmp_path / ".env.uve"


# ============================================================================
# Strict Lookup Tests
# ============================================================================


def test_find_env_file_strict_in_current_dir(tmp_path):
    """Finds .env.uve in current directory (strict mode)."""
    env_file = tmp_path / ".env.uve"
    env_file.touch()

    result = find_env_file_strict(tmp_path)
    assert result == env_file


def test_find_env_file_strict_walk_up_to_root(tmp_path):
    """Walks up directory tree to project root (strict mode)."""
    # Create project structure
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "pyproject.toml").touch()
    (project_root / ".env.uve").touch()

    subdir = project_root / "src" / "mypackage"
    subdir.mkdir(parents=True)

    result = find_env_file_strict(subdir)
    assert result == project_root / ".env.uve"


def test_find_env_file_strict_error_at_project_root(tmp_path):
    """Raises error if .env.uve not found at project root (strict mode)."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "pyproject.toml").touch()

    subdir = project_root / "src"
    subdir.mkdir()

    with pytest.raises(EnvFileError, match=".env.uve not found in project"):
        find_env_file_strict(subdir)


def test_find_env_file_strict_error_no_project(tmp_path):
    """Raises error if no .env.uve and no project root (strict mode)."""
    some_dir = tmp_path / "some_dir"
    some_dir.mkdir()

    with pytest.raises(EnvFileError, match=".env.uve not found starting from"):
        find_env_file_strict(some_dir)


def test_find_env_file_strict_prefers_closest(tmp_path):
    """Prefers .env.uve in closer directory (strict mode)."""
    # Create nested structure with multiple .env.uve files
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "pyproject.toml").touch()
    (project_root / ".env.uve").write_text("ROOT=true\n")

    subdir = project_root / "subdir"
    subdir.mkdir()
    (subdir / ".env.uve").write_text("SUBDIR=true\n")

    # Should find the one in subdir, not root
    result = find_env_file_strict(subdir)
    assert result == subdir / ".env.uve"

    # Verify it's the right file
    env_vars = read_env_file(result)
    assert "SUBDIR" in env_vars


def test_find_env_file_strict_defaults_to_cwd(tmp_path, monkeypatch):
    """Defaults to current working directory (strict mode)."""
    env_file = tmp_path / ".env.uve"
    env_file.touch()

    monkeypatch.chdir(tmp_path)
    result = find_env_file_strict()
    assert result == env_file


# ============================================================================
# Read Tests
# ============================================================================


def test_read_env_file_basic(tmp_path):
    """Reads basic key=value pairs."""
    env_file = tmp_path / ".env.uve"
    env_file.write_text("KEY1=value1\nKEY2=value2\n")

    result = read_env_file(env_file)
    assert result == {"KEY1": "value1", "KEY2": "value2"}


def test_read_env_file_preserves_variables(tmp_path):
    """Variables like ${HOME} are NOT expanded."""
    env_file = tmp_path / ".env.uve"
    env_file.write_text("UV_PROJECT_ENVIRONMENT=${HOME}/prime-uve/venvs/test_abc123\n")

    result = read_env_file(env_file)
    assert result["UV_PROJECT_ENVIRONMENT"] == "${HOME}/prime-uve/venvs/test_abc123"


def test_read_env_file_ignores_comments(tmp_path):
    """Lines starting with # are ignored."""
    env_file = tmp_path / ".env.uve"
    content = """# This is a comment
KEY1=value1
# Another comment
KEY2=value2
"""
    env_file.write_text(content)

    result = read_env_file(env_file)
    assert result == {"KEY1": "value1", "KEY2": "value2"}


def test_read_env_file_ignores_empty_lines(tmp_path):
    """Empty lines are ignored."""
    env_file = tmp_path / ".env.uve"
    content = """KEY1=value1

KEY2=value2


KEY3=value3
"""
    env_file.write_text(content)

    result = read_env_file(env_file)
    assert result == {"KEY1": "value1", "KEY2": "value2", "KEY3": "value3"}


def test_read_env_file_strips_whitespace(tmp_path):
    """Leading/trailing whitespace is stripped."""
    env_file = tmp_path / ".env.uve"
    content = "  KEY1  =  value1  \n\tKEY2\t=\tvalue2\t\n"
    env_file.write_text(content)

    result = read_env_file(env_file)
    assert result == {"KEY1": "value1", "KEY2": "value2"}


def test_read_env_file_empty_file(tmp_path):
    """Empty file returns empty dict."""
    env_file = tmp_path / ".env.uve"
    env_file.write_text("")

    result = read_env_file(env_file)
    assert result == {}


def test_read_env_file_missing_file(tmp_path):
    """Missing file raises EnvFileError."""
    env_file = tmp_path / "nonexistent.env"

    with pytest.raises(EnvFileError, match="File not found"):
        read_env_file(env_file)


@pytest.mark.skipif(sys.platform == "win32", reason="Permission tests unreliable on Windows")
def test_read_env_file_permission_denied(tmp_path):
    """Permission denied raises EnvFileError."""
    env_file = tmp_path / ".env.uve"
    env_file.write_text("KEY=value\n")
    env_file.chmod(0o000)

    try:
        with pytest.raises(EnvFileError, match="Permission denied"):
            read_env_file(env_file)
    finally:
        env_file.chmod(0o644)


# ============================================================================
# Write Tests
# ============================================================================


def test_write_env_file_basic(tmp_path):
    """Writes basic key=value pairs."""
    env_file = tmp_path / ".env.uve"
    env_vars = {"KEY1": "value1", "KEY2": "value2"}

    write_env_file(env_file, env_vars)

    content = env_file.read_text()
    assert content == "KEY1=value1\nKEY2=value2\n"


def test_write_env_file_preserves_variables(tmp_path):
    """Variables like ${HOME} are written as-is."""
    env_file = tmp_path / ".env.uve"
    env_vars = {"UV_PROJECT_ENVIRONMENT": "${HOME}/prime-uve/venvs/test_abc123"}

    write_env_file(env_file, env_vars)

    content = env_file.read_text()
    assert "${HOME}" in content
    assert "UV_PROJECT_ENVIRONMENT=${HOME}/prime-uve/venvs/test_abc123" in content


def test_write_env_file_sorted_keys(tmp_path):
    """Keys are written in sorted order."""
    env_file = tmp_path / ".env.uve"
    env_vars = {"ZEBRA": "last", "ALPHA": "first", "MIDDLE": "mid"}

    write_env_file(env_file, env_vars)

    content = env_file.read_text()
    lines = content.strip().split('\n')
    assert lines == ["ALPHA=first", "MIDDLE=mid", "ZEBRA=last"]


def test_write_env_file_overwrites_existing(tmp_path):
    """Overwrites existing file."""
    env_file = tmp_path / ".env.uve"
    env_file.write_text("OLD=value\n")

    env_vars = {"NEW": "value"}
    write_env_file(env_file, env_vars)

    content = env_file.read_text()
    assert content == "NEW=value\n"
    assert "OLD" not in content


def test_write_env_file_creates_parent_dirs(tmp_path):
    """Creates parent directories if missing."""
    env_file = tmp_path / "subdir" / "nested" / ".env.uve"
    env_vars = {"KEY": "value"}

    write_env_file(env_file, env_vars)

    assert env_file.exists()
    assert env_file.read_text() == "KEY=value\n"


def test_write_env_file_empty_dict(tmp_path):
    """Empty dict creates empty file."""
    env_file = tmp_path / ".env.uve"
    write_env_file(env_file, {})

    assert env_file.exists()
    assert env_file.read_text() == ""


@pytest.mark.skipif(sys.platform == "win32", reason="Permission tests unreliable on Windows")
def test_write_env_file_permission_denied(tmp_path):
    """Permission denied raises EnvFileError."""
    readonly_dir = tmp_path / "readonly"
    readonly_dir.mkdir()
    readonly_dir.chmod(0o444)

    env_file = readonly_dir / ".env.uve"

    try:
        with pytest.raises(EnvFileError, match="Permission denied"):
            write_env_file(env_file, {"KEY": "value"})
    finally:
        readonly_dir.chmod(0o755)


# ============================================================================
# Update Tests
# ============================================================================


def test_update_env_file_adds_new_var(tmp_path):
    """Adding new variable preserves existing ones."""
    env_file = tmp_path / ".env.uve"
    env_file.write_text("KEY1=value1\n")

    update_env_file(env_file, {"KEY2": "value2"})

    result = read_env_file(env_file)
    assert result == {"KEY1": "value1", "KEY2": "value2"}


def test_update_env_file_updates_existing_var(tmp_path):
    """Updating existing variable changes only that one."""
    env_file = tmp_path / ".env.uve"
    env_file.write_text("KEY1=old\nKEY2=keep\n")

    update_env_file(env_file, {"KEY1": "new"})

    result = read_env_file(env_file)
    assert result == {"KEY1": "new", "KEY2": "keep"}


def test_update_env_file_creates_file_if_missing(tmp_path):
    """Creates file if it doesn't exist."""
    env_file = tmp_path / ".env.uve"

    update_env_file(env_file, {"KEY": "value"})

    assert env_file.exists()
    result = read_env_file(env_file)
    assert result == {"KEY": "value"}


def test_update_env_file_preserves_order(tmp_path):
    """Variables are sorted alphabetically."""
    env_file = tmp_path / ".env.uve"
    env_file.write_text("ZEBRA=last\nALPHA=first\n")

    update_env_file(env_file, {"MIDDLE": "mid"})

    content = env_file.read_text()
    lines = content.strip().split('\n')
    assert lines == ["ALPHA=first", "MIDDLE=mid", "ZEBRA=last"]


# ============================================================================
# Get Venv Path Tests
# ============================================================================


def test_get_venv_path_no_expand():
    """Returns path with variables unexpanded."""
    env_vars = {"UV_PROJECT_ENVIRONMENT": "${HOME}/prime-uve/venvs/test_abc123"}

    result = get_venv_path(env_vars, expand=False)

    assert result == "${HOME}/prime-uve/venvs/test_abc123"
    assert isinstance(result, str)


def test_get_venv_path_expand():
    """Expands ${HOME} when expand=True."""
    env_vars = {"UV_PROJECT_ENVIRONMENT": "${HOME}/prime-uve/venvs/test_abc123"}

    result = get_venv_path(env_vars, expand=True)

    assert isinstance(result, Path)
    assert "${HOME}" not in str(result)
    # Check path components (works on both Unix and Windows)
    assert "prime-uve" in str(result)
    assert "venvs" in str(result)
    assert "test_abc123" in str(result)


def test_get_venv_path_missing_var():
    """Raises EnvFileError if UV_PROJECT_ENVIRONMENT not found."""
    env_vars = {"OTHER_VAR": "value"}

    with pytest.raises(EnvFileError, match="UV_PROJECT_ENVIRONMENT not found"):
        get_venv_path(env_vars)


def test_get_venv_path_empty_value():
    """Raises EnvFileError if UV_PROJECT_ENVIRONMENT is empty."""
    env_vars = {"UV_PROJECT_ENVIRONMENT": ""}

    with pytest.raises(EnvFileError, match="UV_PROJECT_ENVIRONMENT is empty"):
        get_venv_path(env_vars)


def test_get_venv_path_whitespace_value():
    """Raises EnvFileError if UV_PROJECT_ENVIRONMENT is only whitespace."""
    env_vars = {"UV_PROJECT_ENVIRONMENT": "   "}

    with pytest.raises(EnvFileError, match="UV_PROJECT_ENVIRONMENT is empty"):
        get_venv_path(env_vars)


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_workflow_find_read_write(tmp_path):
    """Full workflow: find → read → update → read again."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "pyproject.toml").touch()

    # Find (creates .env.uve)
    env_file = find_env_file(project_root)
    assert env_file == project_root / ".env.uve"

    # Write initial value
    write_env_file(env_file, {"UV_PROJECT_ENVIRONMENT": "${HOME}/prime-uve/venvs/proj_abc123"})

    # Read back
    env_vars = read_env_file(env_file)
    assert env_vars["UV_PROJECT_ENVIRONMENT"] == "${HOME}/prime-uve/venvs/proj_abc123"

    # Update
    update_env_file(env_file, {"PYTHONPATH": "/some/path"})

    # Read again
    env_vars = read_env_file(env_file)
    assert len(env_vars) == 2
    assert env_vars["UV_PROJECT_ENVIRONMENT"] == "${HOME}/prime-uve/venvs/proj_abc123"
    assert env_vars["PYTHONPATH"] == "/some/path"


def test_cross_platform_path_preserved(tmp_path):
    """${HOME} syntax preserved through read/write cycle."""
    env_file = tmp_path / ".env.uve"
    original = {"UV_PROJECT_ENVIRONMENT": "${HOME}/prime-uve/venvs/test_abc123"}

    # Write
    write_env_file(env_file, original)

    # Read
    result = read_env_file(env_file)

    # Write again
    write_env_file(env_file, result)

    # Read again
    final = read_env_file(env_file)

    # Should still have ${HOME}, not expanded
    assert final["UV_PROJECT_ENVIRONMENT"] == "${HOME}/prime-uve/venvs/test_abc123"


def test_multiple_variables(tmp_path):
    """Multiple environment variables handled correctly."""
    env_file = tmp_path / ".env.uve"
    env_vars = {
        "UV_PROJECT_ENVIRONMENT": "${HOME}/prime-uve/venvs/test_abc123",
        "PYTHONPATH": "/some/path",
        "CUSTOM_VAR": "custom_value",
        "ANOTHER_VAR": "${HOME}/another/path",
    }

    write_env_file(env_file, env_vars)
    result = read_env_file(env_file)

    assert result == env_vars
    # Verify variables not expanded
    assert "${HOME}" in result["UV_PROJECT_ENVIRONMENT"]
    assert "${HOME}" in result["ANOTHER_VAR"]


# ============================================================================
# Edge Cases
# ============================================================================


def test_malformed_lines_ignored(tmp_path):
    """Lines without '=' are ignored gracefully."""
    env_file = tmp_path / ".env.uve"
    content = """KEY1=value1
this line has no equals sign
KEY2=value2
another malformed line
"""
    env_file.write_text(content)

    result = read_env_file(env_file)
    assert result == {"KEY1": "value1", "KEY2": "value2"}


def test_equals_in_value(tmp_path):
    """Values containing '=' are handled correctly."""
    env_file = tmp_path / ".env.uve"
    env_file.write_text("FORMULA=a=b+c\n")

    result = read_env_file(env_file)
    assert result["FORMULA"] == "a=b+c"


def test_unicode_in_values(tmp_path):
    """Unicode characters in values work correctly."""
    env_file = tmp_path / ".env.uve"
    env_vars = {
        "KEY1": "Hello 世界",
        "KEY2": "Привет мир",
        "KEY3": "مرحبا بالعالم",
    }

    write_env_file(env_file, env_vars)
    result = read_env_file(env_file)

    assert result == env_vars


def test_very_long_values(tmp_path):
    """Very long values work correctly."""
    env_file = tmp_path / ".env.uve"
    long_value = "x" * 10000
    env_vars = {"LONG_KEY": long_value}

    write_env_file(env_file, env_vars)
    result = read_env_file(env_file)

    assert result["LONG_KEY"] == long_value


def test_symlink_env_file(tmp_path):
    """Symlinked .env.uve files work correctly."""
    # Create actual file
    actual_file = tmp_path / "actual.env"
    actual_file.write_text("KEY=value\n")

    # Create symlink
    symlink = tmp_path / ".env.uve"
    if sys.platform == "win32":
        # On Windows, skip if we can't create symlinks
        try:
            symlink.symlink_to(actual_file)
        except OSError:
            pytest.skip("Cannot create symlinks on Windows without admin")
    else:
        symlink.symlink_to(actual_file)

    result = read_env_file(symlink)
    assert result == {"KEY": "value"}


def test_empty_key_ignored(tmp_path):
    """Lines with empty keys are ignored."""
    env_file = tmp_path / ".env.uve"
    content = """KEY1=value1
=empty_key
KEY2=value2
"""
    env_file.write_text(content)

    result = read_env_file(env_file)
    assert result == {"KEY1": "value1", "KEY2": "value2"}


def test_find_env_file_prefers_closest(tmp_path):
    """Prefers .env.uve in closer directory."""
    # Create nested structure with multiple .env.uve files
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "pyproject.toml").touch()
    (project_root / ".env.uve").write_text("ROOT=true\n")

    subdir = project_root / "subdir"
    subdir.mkdir()
    (subdir / ".env.uve").write_text("SUBDIR=true\n")

    # Should find the one in subdir, not root
    result = find_env_file(subdir)
    assert result == subdir / ".env.uve"

    # Verify it's the right file
    env_vars = read_env_file(result)
    assert "SUBDIR" in env_vars


def test_comment_with_equals(tmp_path):
    """Comments containing '=' are ignored."""
    env_file = tmp_path / ".env.uve"
    content = """# This comment has KEY=VALUE in it
KEY1=value1
# KEY2=commented_out
KEY3=value3
"""
    env_file.write_text(content)

    result = read_env_file(env_file)
    assert result == {"KEY1": "value1", "KEY3": "value3"}
    assert "KEY2" not in result


def test_trailing_whitespace_in_value(tmp_path):
    """Trailing whitespace in values is stripped."""
    env_file = tmp_path / ".env.uve"
    env_file.write_text("KEY=value   \n")

    result = read_env_file(env_file)
    assert result["KEY"] == "value"


def test_get_venv_path_with_expanded_actual_path():
    """Expanded path points to a real location under home directory."""
    env_vars = {"UV_PROJECT_ENVIRONMENT": "${HOME}/prime-uve/venvs/test_abc123"}

    result = get_venv_path(env_vars, expand=True)

    # Should be an absolute path
    assert result.is_absolute()

    # Should contain the home directory
    home = Path.home()
    assert str(home) in str(result)


def test_find_env_file_permission_error_on_create(tmp_path, monkeypatch):
    """Raises EnvFileError if cannot create .env.uve due to permissions."""
    # Create a scenario where we can't create the file
    # We'll mock Path.touch to raise PermissionError
    from unittest.mock import MagicMock

    original_touch = Path.touch

    def mock_touch(self, *args, **kwargs):
        if self.name == ".env.uve":
            raise PermissionError("Mocked permission error")
        return original_touch(self, *args, **kwargs)

    monkeypatch.setattr(Path, "touch", mock_touch)

    with pytest.raises(EnvFileError, match="Cannot create .env.uve"):
        find_env_file(tmp_path)


def test_read_env_file_oserror(tmp_path, monkeypatch):
    """Raises EnvFileError for generic OSError."""
    env_file = tmp_path / ".env.uve"
    env_file.touch()

    # Mock read_text to raise OSError
    original_read_text = Path.read_text

    def mock_read_text(self, *args, **kwargs):
        if self.name == ".env.uve":
            raise OSError("Mocked OS error")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", mock_read_text)

    with pytest.raises(EnvFileError, match="Cannot read file"):
        read_env_file(env_file)


def test_read_env_file_permission_error_mocked(tmp_path, monkeypatch):
    """Raises EnvFileError for PermissionError during read."""
    env_file = tmp_path / ".env.uve"
    env_file.touch()

    # Mock read_text to raise PermissionError
    original_read_text = Path.read_text

    def mock_read_text(self, *args, **kwargs):
        if self.name == ".env.uve":
            raise PermissionError("Mocked permission error")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", mock_read_text)

    with pytest.raises(EnvFileError, match="Permission denied"):
        read_env_file(env_file)


def test_write_env_file_parent_dir_permission_error(tmp_path, monkeypatch):
    """Raises EnvFileError if cannot create parent directory."""
    env_file = tmp_path / "subdir" / ".env.uve"

    # Mock mkdir to raise PermissionError
    original_mkdir = Path.mkdir

    def mock_mkdir(self, *args, **kwargs):
        if "subdir" in str(self):
            raise PermissionError("Mocked permission error")
        return original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", mock_mkdir)

    with pytest.raises(EnvFileError, match="Cannot create parent directory"):
        write_env_file(env_file, {"KEY": "value"})


def test_write_env_file_oserror(tmp_path, monkeypatch):
    """Raises EnvFileError for generic OSError during write."""
    env_file = tmp_path / ".env.uve"

    # Mock write_text to raise OSError
    original_write_text = Path.write_text

    def mock_write_text(self, *args, **kwargs):
        if self.name == ".env.uve":
            raise OSError("Mocked OS error")
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", mock_write_text)

    with pytest.raises(EnvFileError, match="Cannot write file"):
        write_env_file(env_file, {"KEY": "value"})


def test_write_env_file_permission_error_mocked(tmp_path, monkeypatch):
    """Raises EnvFileError for PermissionError during write."""
    env_file = tmp_path / ".env.uve"

    # Mock write_text to raise PermissionError
    original_write_text = Path.write_text

    def mock_write_text(self, *args, **kwargs):
        if self.name == ".env.uve":
            raise PermissionError("Mocked permission error")
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", mock_write_text)

    with pytest.raises(EnvFileError, match="Permission denied"):
        write_env_file(env_file, {"KEY": "value"})
