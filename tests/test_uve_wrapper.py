"""Tests for uve wrapper."""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from prime_uve.uve.wrapper import is_uv_available, main


# Fixtures


@pytest.fixture
def mock_env_file(tmp_path):
    """Create a mock .env.uve file."""
    env_file = tmp_path / ".env.uve"
    env_file.write_text("UV_PROJECT_ENVIRONMENT=${HOME}/prime-uve/venvs/test_12345678\n")
    return env_file


@pytest.fixture
def mock_find_env_file(mock_env_file):
    """Mock find_env_file to return test env file."""
    with patch("prime_uve.uve.wrapper.find_env_file", return_value=mock_env_file):
        yield mock_env_file


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run."""
    with patch("prime_uve.uve.wrapper.subprocess.run") as mock_run:
        # Default: return success
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        yield mock_run


@pytest.fixture
def mock_is_uv_available():
    """Mock is_uv_available to return True."""
    with patch("prime_uve.uve.wrapper.is_uv_available", return_value=True):
        yield


# Tests for is_uv_available()


def test_is_uv_available_true():
    """Detects when uv is available."""
    with patch("shutil.which", return_value="/usr/bin/uv"):
        assert is_uv_available() is True


def test_is_uv_available_false():
    """Detects when uv is not available."""
    with patch("shutil.which", return_value=None):
        assert is_uv_available() is False


# Tests for main() - Basic Functionality


def test_main_finds_env_file(mock_find_env_file, mock_subprocess, mock_is_uv_available):
    """uve finds .env.uve in current directory."""
    with patch("sys.argv", ["uve", "sync"]), pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    # Verify subprocess was called with env file
    mock_subprocess.assert_called_once()
    cmd = mock_subprocess.call_args[0][0]
    assert str(mock_find_env_file) in cmd


def test_main_passes_args_to_uv(mock_find_env_file, mock_subprocess, mock_is_uv_available):
    """Arguments are passed through to uv."""
    with patch("sys.argv", ["uve", "add", "requests", "--dev"]), pytest.raises(
        SystemExit
    ) as exc_info:
        main()

    assert exc_info.value.code == 0
    cmd = mock_subprocess.call_args[0][0]
    assert "add" in cmd
    assert "requests" in cmd
    assert "--dev" in cmd


def test_main_forwards_exit_code(mock_find_env_file, mock_subprocess, mock_is_uv_available):
    """Exit code from uv is forwarded."""
    # Mock uv returning exit code 42
    mock_result = MagicMock()
    mock_result.returncode = 42
    mock_subprocess.return_value = mock_result

    with patch("sys.argv", ["uve", "sync"]), pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 42


def test_main_with_no_args(mock_find_env_file, mock_subprocess, mock_is_uv_available):
    """Works with no arguments (uve → uv run --env-file .env.uve -- uv)."""
    with patch("sys.argv", ["uve"]), pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    cmd = mock_subprocess.call_args[0][0]
    # Should be: uv run --env-file <path> -- uv
    assert cmd[:2] == ["uv", "run"]
    assert "--env-file" in cmd
    assert "--" in cmd
    assert cmd[cmd.index("--") + 1] == "uv"


# Tests for Command Construction


def test_main_constructs_correct_command(
    mock_find_env_file, mock_subprocess, mock_is_uv_available
):
    """Verify exact command: uv run --env-file .env.uve -- uv [args]."""
    with patch("sys.argv", ["uve", "add", "requests"]), pytest.raises(SystemExit):
        main()

    cmd = mock_subprocess.call_args[0][0]
    expected_prefix = ["uv", "run", "--env-file", str(mock_find_env_file), "--", "uv"]
    assert cmd[: len(expected_prefix)] == expected_prefix
    assert cmd[len(expected_prefix) :] == ["add", "requests"]


def test_main_with_multiple_args(mock_find_env_file, mock_subprocess, mock_is_uv_available):
    """Works with multiple arguments."""
    with patch("sys.argv", ["uve", "run", "python", "-c", "print('hello')"]), pytest.raises(
        SystemExit
    ):
        main()

    cmd = mock_subprocess.call_args[0][0]
    assert "run" in cmd
    assert "python" in cmd
    assert "-c" in cmd
    assert "print('hello')" in cmd


def test_main_with_flags(mock_find_env_file, mock_subprocess, mock_is_uv_available):
    """Preserves flags like --verbose."""
    with patch("sys.argv", ["uve", "--verbose", "sync"]), pytest.raises(SystemExit):
        main()

    cmd = mock_subprocess.call_args[0][0]
    assert "--verbose" in cmd


# Tests for Environment Variables


def test_main_sets_home_on_windows(mock_find_env_file, mock_subprocess, mock_is_uv_available):
    """On Windows, HOME is set if missing."""
    with (
        patch("sys.platform", "win32"),
        patch.dict(os.environ, {"USERPROFILE": "C:\\Users\\test"}, clear=True),
        patch("sys.argv", ["uve", "sync"]),
        pytest.raises(SystemExit),
    ):
        main()

    # Check that env passed to subprocess has HOME set
    env = mock_subprocess.call_args[1]["env"]
    assert env["HOME"] == "C:\\Users\\test"


def test_main_preserves_existing_home(mock_find_env_file, mock_subprocess, mock_is_uv_available):
    """Existing HOME variable is not overridden."""
    with (
        patch("sys.platform", "win32"),
        patch.dict(os.environ, {"HOME": "/custom/home", "USERPROFILE": "C:\\Users\\test"}),
        patch("sys.argv", ["uve", "sync"]),
        pytest.raises(SystemExit),
    ):
        main()

    env = mock_subprocess.call_args[1]["env"]
    assert env["HOME"] == "/custom/home"


def test_main_windows_home_from_userprofile(
    mock_find_env_file, mock_subprocess, mock_is_uv_available
):
    """On Windows, HOME set from USERPROFILE if missing."""
    with (
        patch("sys.platform", "win32"),
        patch.dict(os.environ, {"USERPROFILE": "C:\\Users\\testuser"}, clear=True),
        patch("sys.argv", ["uve", "sync"]),
        pytest.raises(SystemExit),
    ):
        main()

    env = mock_subprocess.call_args[1]["env"]
    assert env["HOME"] == "C:\\Users\\testuser"


def test_main_windows_home_fallback(mock_find_env_file, mock_subprocess, mock_is_uv_available):
    """On Windows, falls back to expanduser if USERPROFILE missing."""
    with (
        patch("sys.platform", "win32"),
        patch.dict(os.environ, {}, clear=True),
        patch("os.path.expanduser", return_value="C:\\Users\\fallback"),
        patch("sys.argv", ["uve", "sync"]),
        pytest.raises(SystemExit),
    ):
        main()

    env = mock_subprocess.call_args[1]["env"]
    assert env["HOME"] == "C:\\Users\\fallback"


def test_main_unix_no_home_modification(
    mock_find_env_file, mock_subprocess, mock_is_uv_available
):
    """On Unix, HOME is not modified."""
    original_home = "/home/user"
    with (
        patch("sys.platform", "linux"),
        patch.dict(os.environ, {"HOME": original_home}),
        patch("sys.argv", ["uve", "sync"]),
        pytest.raises(SystemExit),
    ):
        main()

    env = mock_subprocess.call_args[1]["env"]
    assert env["HOME"] == original_home


# Tests for Error Handling


def test_main_uv_not_found(mock_find_env_file, mock_subprocess, capsys):
    """Clear error when uv not found."""
    with (
        patch("prime_uve.uve.wrapper.is_uv_available", return_value=False),
        patch("sys.argv", ["uve", "sync"]),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "uv' command not found" in captured.err
    assert "https://github.com/astral-sh/uv" in captured.err


def test_main_env_file_not_found_error(capsys, mock_subprocess, mock_is_uv_available):
    """Error when .env.uve cannot be found/created."""
    with (
        patch(
            "prime_uve.uve.wrapper.find_env_file",
            side_effect=Exception("Permission denied"),
        ),
        patch("sys.argv", ["uve", "sync"]),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error finding .env.uve" in captured.err
    assert "Permission denied" in captured.err


def test_main_subprocess_error(mock_find_env_file, capsys, mock_is_uv_available):
    """Handles subprocess errors gracefully."""
    with (
        patch(
            "prime_uve.uve.wrapper.subprocess.run",
            side_effect=Exception("Subprocess error"),
        ),
        patch("sys.argv", ["uve", "sync"]),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error running uv" in captured.err
    assert "Subprocess error" in captured.err


def test_main_keyboard_interrupt(mock_find_env_file, mock_is_uv_available):
    """Handles Ctrl+C (KeyboardInterrupt) gracefully."""
    with (
        patch("prime_uve.uve.wrapper.subprocess.run", side_effect=KeyboardInterrupt),
        patch("sys.argv", ["uve", "sync"]),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()

    assert exc_info.value.code == 130


def test_main_uv_command_fails(mock_find_env_file, mock_subprocess, mock_is_uv_available):
    """Forwards non-zero exit code from uv."""
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_subprocess.return_value = mock_result

    with patch("sys.argv", ["uve", "add", "nonexistent"]), pytest.raises(
        SystemExit
    ) as exc_info:
        main()

    assert exc_info.value.code == 1


# Tests for Integration


def test_main_with_empty_env_file(tmp_path, mock_subprocess, mock_is_uv_available):
    """Works with empty .env.uve file."""
    env_file = tmp_path / ".env.uve"
    env_file.write_text("")  # Empty file

    with (
        patch("prime_uve.uve.wrapper.find_env_file", return_value=env_file),
        patch("sys.argv", ["uve", "sync"]),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()

    assert exc_info.value.code == 0
    # Should still pass the env file to uv
    cmd = mock_subprocess.call_args[0][0]
    assert str(env_file) in cmd


def test_main_with_comments_only(tmp_path, mock_subprocess, mock_is_uv_available):
    """Works with .env.uve containing only comments."""
    env_file = tmp_path / ".env.uve"
    env_file.write_text("# This is a comment\n# Another comment\n")

    with (
        patch("prime_uve.uve.wrapper.find_env_file", return_value=env_file),
        patch("sys.argv", ["uve", "sync"]),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()

    assert exc_info.value.code == 0


def test_main_full_workflow(mock_find_env_file, mock_subprocess, mock_is_uv_available):
    """Full workflow: find env file, set HOME, run uv."""
    with (
        patch("sys.platform", "win32"),
        patch.dict(os.environ, {"USERPROFILE": "C:\\Users\\test"}, clear=True),
        patch("sys.argv", ["uve", "add", "requests"]),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()

    assert exc_info.value.code == 0

    # Verify command construction
    cmd = mock_subprocess.call_args[0][0]
    assert cmd[0] == "uv"
    assert cmd[1] == "run"
    assert "--env-file" in cmd
    assert "--" in cmd
    assert "add" in cmd
    assert "requests" in cmd

    # Verify HOME was set
    env = mock_subprocess.call_args[1]["env"]
    assert env["HOME"] == "C:\\Users\\test"


def test_main_does_not_expand_env_file_vars(
    tmp_path, mock_subprocess, mock_is_uv_available
):
    """Variables in .env.uve are NOT expanded by uve (left to uv)."""
    env_file = tmp_path / ".env.uve"
    # Write file with ${HOME} variable
    env_file.write_text("UV_PROJECT_ENVIRONMENT=${HOME}/prime-uve/venvs/test_12345678\n")

    with (
        patch("prime_uve.uve.wrapper.find_env_file", return_value=env_file),
        patch("sys.argv", ["uve", "sync"]),
        pytest.raises(SystemExit),
    ):
        main()

    # uve just passes the path to the file, doesn't read or expand it
    cmd = mock_subprocess.call_args[0][0]
    assert str(env_file) in cmd
    # The file content is NOT parsed or expanded by uve
