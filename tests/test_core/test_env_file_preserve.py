"""Tests for update_env_file_preserve_format function."""

from pathlib import Path

import pytest

from prime_uve.core.env_file import update_env_file_preserve_format


def test_preserve_format_adds_to_empty_file(tmp_path):
    """Test adding variable to empty file."""
    env_file = tmp_path / ".env.uve"
    env_file.write_text("")

    update_env_file_preserve_format(env_file, {"UV_PROJECT_ENVIRONMENT": "${HOME}/venvs/test"})

    content = env_file.read_text()
    assert "UV_PROJECT_ENVIRONMENT=${HOME}/venvs/test" in content


def test_preserve_format_adds_to_new_file(tmp_path):
    """Test adding variable to non-existent file."""
    env_file = tmp_path / ".env.uve"

    update_env_file_preserve_format(env_file, {"UV_PROJECT_ENVIRONMENT": "${HOME}/venvs/test"})

    assert env_file.exists()
    content = env_file.read_text()
    assert "UV_PROJECT_ENVIRONMENT=${HOME}/venvs/test" in content


def test_preserve_format_preserves_comments(tmp_path):
    """Test that comments are preserved."""
    env_file = tmp_path / ".env.uve"
    env_file.write_text(
        """# This is a comment
DATABASE_URL=postgres://localhost
# Another comment
API_KEY=secret
"""
    )

    update_env_file_preserve_format(env_file, {"UV_PROJECT_ENVIRONMENT": "${HOME}/venvs/test"})

    content = env_file.read_text()
    assert "# This is a comment" in content
    assert "# Another comment" in content
    assert "DATABASE_URL=postgres://localhost" in content
    assert "API_KEY=secret" in content
    assert "UV_PROJECT_ENVIRONMENT=${HOME}/venvs/test" in content


def test_preserve_format_preserves_blank_lines(tmp_path):
    """Test that blank lines are preserved."""
    env_file = tmp_path / ".env.uve"
    env_file.write_text(
        """DATABASE_URL=postgres://localhost

API_KEY=secret
"""
    )

    update_env_file_preserve_format(env_file, {"UV_PROJECT_ENVIRONMENT": "${HOME}/venvs/test"})

    lines = env_file.read_text().splitlines()
    # Should have blank line between DATABASE_URL and API_KEY
    assert lines[1] == ""


def test_preserve_format_updates_existing_variable(tmp_path):
    """Test updating existing variable in place."""
    env_file = tmp_path / ".env.uve"
    env_file.write_text(
        """DATABASE_URL=postgres://localhost
UV_PROJECT_ENVIRONMENT=${HOME}/venvs/old
API_KEY=secret
"""
    )

    update_env_file_preserve_format(env_file, {"UV_PROJECT_ENVIRONMENT": "${HOME}/venvs/new"})

    content = env_file.read_text()
    lines = content.splitlines()

    # Check order preserved
    assert lines[0] == "DATABASE_URL=postgres://localhost"
    assert lines[1] == "UV_PROJECT_ENVIRONMENT=${HOME}/venvs/new"
    assert lines[2] == "API_KEY=secret"

    # Old value should not appear
    assert "old" not in content
    assert "new" in content


def test_preserve_format_appends_new_variable(tmp_path):
    """Test appending new variable at end."""
    env_file = tmp_path / ".env.uve"
    env_file.write_text(
        """# My variables
DATABASE_URL=postgres://localhost
API_KEY=secret
"""
    )

    update_env_file_preserve_format(env_file, {"UV_PROJECT_ENVIRONMENT": "${HOME}/venvs/test"})

    lines = env_file.read_text().splitlines()

    # New variable should be at the end
    assert lines[-1] == "UV_PROJECT_ENVIRONMENT=${HOME}/venvs/test"

    # Original order preserved
    assert lines[0] == "# My variables"
    assert lines[1] == "DATABASE_URL=postgres://localhost"
    assert lines[2] == "API_KEY=secret"


def test_preserve_format_updates_multiple_variables(tmp_path):
    """Test updating multiple variables."""
    env_file = tmp_path / ".env.uve"
    env_file.write_text(
        """DATABASE_URL=postgres://localhost
API_KEY=old_key
DEBUG=true
"""
    )

    update_env_file_preserve_format(
        env_file,
        {"API_KEY": "new_key", "UV_PROJECT_ENVIRONMENT": "${HOME}/venvs/test"},
    )

    content = env_file.read_text()
    lines = content.splitlines()

    # API_KEY updated in place
    assert lines[1] == "API_KEY=new_key"
    # UV_PROJECT_ENVIRONMENT appended
    assert lines[3] == "UV_PROJECT_ENVIRONMENT=${HOME}/venvs/test"
    # Others preserved
    assert lines[0] == "DATABASE_URL=postgres://localhost"
    assert lines[2] == "DEBUG=true"


def test_preserve_format_complex_file(tmp_path):
    """Test with a complex real-world file."""
    env_file = tmp_path / ".env.uve"
    env_file.write_text(
        """# Database configuration
DATABASE_URL=postgresql://localhost/mydb

# API keys
API_KEY=secret123
STRIPE_KEY=sk_test_xxx

# Debug settings
DEBUG=true
"""
    )

    update_env_file_preserve_format(env_file, {"UV_PROJECT_ENVIRONMENT": "${HOME}/venvs/proj_abc"})

    content = env_file.read_text()

    # All original content preserved
    assert "# Database configuration" in content
    assert "DATABASE_URL=postgresql://localhost/mydb" in content
    assert "# API keys" in content
    assert "API_KEY=secret123" in content
    assert "STRIPE_KEY=sk_test_xxx" in content
    assert "# Debug settings" in content
    assert "DEBUG=true" in content

    # New variable added
    assert "UV_PROJECT_ENVIRONMENT=${HOME}/venvs/proj_abc" in content

    # Should be at the end
    lines = content.splitlines()
    assert lines[-1] == "UV_PROJECT_ENVIRONMENT=${HOME}/venvs/proj_abc"
