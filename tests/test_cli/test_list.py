"""Tests for the list command."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from prime_uve.cli.list import (
    ValidationResult,
    format_bytes,
    get_disk_usage,
    list_command,
    truncate_path,
    validate_project_mapping,
)
from prime_uve.cli.main import cli


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_cache(tmp_path):
    """Mock cache with test data."""
    cache_data = {
        str(tmp_path / "project1"): {
            "venv_path": "${HOME}/prime-uve/venvs/project1_abc123",
            "project_name": "project1",
            "path_hash": "abc123",
            "created_at": "2025-12-01T10:00:00Z",
        },
        str(tmp_path / "project2"): {
            "venv_path": "${HOME}/prime-uve/venvs/project2_def456",
            "project_name": "project2",
            "path_hash": "def456",
            "created_at": "2025-12-02T11:00:00Z",
        },
    }
    return cache_data


class TestValidateProjectMapping:
    """Tests for validate_project_mapping function."""

    def test_validate_valid_project(self, tmp_path):
        """Test validation when cache matches .env.uve."""
        # Setup
        project_path = tmp_path / "test_project"
        project_path.mkdir()

        venv_path = "${HOME}/prime-uve/venvs/test_abc123"
        env_file = project_path / ".env.uve"
        env_file.write_text(f"UV_PROJECT_ENVIRONMENT={venv_path}\n")

        cache_entry = {
            "venv_path": venv_path,
            "project_name": "test",
            "path_hash": "abc123",
            "created_at": "2025-12-01T10:00:00Z",
        }

        # Execute
        result = validate_project_mapping(str(project_path), cache_entry)

        # Assert
        assert result.is_valid is True
        assert result.project_name == "test"
        assert result.venv_path == venv_path
        assert result.env_venv_path == venv_path

    def test_validate_orphan_mismatch(self, tmp_path):
        """Test validation when cache doesn't match .env.uve."""
        # Setup
        project_path = tmp_path / "test_project"
        project_path.mkdir()

        cache_venv_path = "${HOME}/prime-uve/venvs/test_abc123"
        env_venv_path = "${HOME}/prime-uve/venvs/test_xyz789"  # Different!

        env_file = project_path / ".env.uve"
        env_file.write_text(f"UV_PROJECT_ENVIRONMENT={env_venv_path}\n")

        cache_entry = {
            "venv_path": cache_venv_path,
            "project_name": "test",
            "path_hash": "abc123",
            "created_at": "2025-12-01T10:00:00Z",
        }

        # Execute
        result = validate_project_mapping(str(project_path), cache_entry)

        # Assert
        assert result.is_valid is False
        assert result.venv_path == cache_venv_path
        assert result.env_venv_path == env_venv_path

    def test_validate_orphan_missing_env(self, tmp_path):
        """Test validation when .env.uve is missing."""
        # Setup
        project_path = tmp_path / "test_project"
        project_path.mkdir()
        # No .env.uve file created

        cache_entry = {
            "venv_path": "${HOME}/prime-uve/venvs/test_abc123",
            "project_name": "test",
            "path_hash": "abc123",
            "created_at": "2025-12-01T10:00:00Z",
        }

        # Execute
        result = validate_project_mapping(str(project_path), cache_entry)

        # Assert
        assert result.is_valid is False
        assert result.env_venv_path is None

    def test_validate_permission_error(self, tmp_path, monkeypatch):
        """Test handling of permission errors when reading .env.uve."""
        # Setup
        project_path = tmp_path / "test_project"
        project_path.mkdir()

        env_file = project_path / ".env.uve"
        env_file.write_text("UV_PROJECT_ENVIRONMENT=${HOME}/test\n")

        cache_entry = {
            "venv_path": "${HOME}/prime-uve/venvs/test_abc123",
            "project_name": "test",
            "path_hash": "abc123",
            "created_at": "2025-12-01T10:00:00Z",
        }

        # Mock read_env_file to raise exception
        def mock_read_env_file(path):
            raise PermissionError("Access denied")

        monkeypatch.setattr("prime_uve.cli.list.read_env_file", mock_read_env_file)

        # Execute
        result = validate_project_mapping(str(project_path), cache_entry)

        # Assert - should handle error gracefully and mark as invalid
        assert result.is_valid is False


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_format_bytes_zero(self):
        """Test formatting zero bytes."""
        assert format_bytes(0) == "0 B"

    def test_format_bytes_bytes(self):
        """Test formatting bytes."""
        assert format_bytes(500) == "500 B"

    def test_format_bytes_kilobytes(self):
        """Test formatting kilobytes."""
        assert format_bytes(1024) == "1.0 KB"
        assert format_bytes(1536) == "1.5 KB"

    def test_format_bytes_megabytes(self):
        """Test formatting megabytes."""
        assert format_bytes(1024 * 1024) == "1.0 MB"
        assert format_bytes(1024 * 1024 * 125) == "125.0 MB"

    def test_format_bytes_gigabytes(self):
        """Test formatting gigabytes."""
        assert format_bytes(1024 * 1024 * 1024) == "1.0 GB"

    def test_truncate_path_short(self):
        """Test truncating path that's already short enough."""
        path = "~/venvs/test"
        assert truncate_path(path, 20) == path

    def test_truncate_path_long(self):
        """Test truncating long path."""
        path = "~/very/long/path/to/virtual/environment/directory"
        truncated = truncate_path(path, 20)
        assert len(truncated) == 20
        assert truncated.startswith("...")
        assert truncated.endswith("directory")

    def test_get_disk_usage_empty_dir(self, tmp_path):
        """Test disk usage calculation for empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        assert get_disk_usage(empty_dir) == 0

    def test_get_disk_usage_with_files(self, tmp_path):
        """Test disk usage calculation with files."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        # Create test files
        (test_dir / "file1.txt").write_text("a" * 100)
        (test_dir / "file2.txt").write_text("b" * 200)

        subdir = test_dir / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("c" * 300)

        usage = get_disk_usage(test_dir)
        assert usage == 600  # 100 + 200 + 300

    def test_get_disk_usage_nonexistent(self, tmp_path):
        """Test disk usage for non-existent directory."""
        nonexistent = tmp_path / "does_not_exist"
        assert get_disk_usage(nonexistent) == 0


class TestListCommandCLI:
    """Tests for list command via CLI."""

    def test_list_empty_cache(self, runner, tmp_path, monkeypatch):
        """Test list with empty cache shows helpful message."""
        # Mock cache to return empty mappings
        mock_cache_instance = Mock()
        mock_cache_instance.list_all.return_value = {}

        def mock_cache_init(self):
            return mock_cache_instance

        monkeypatch.setattr("prime_uve.cli.list.Cache", lambda: mock_cache_instance)

        # Execute
        result = runner.invoke(cli, ["list"])

        # Assert
        assert result.exit_code == 0
        assert "No managed virtual environments found" in result.output
        assert "prime-uve init" in result.output

    def test_list_empty_cache_json(self, runner, monkeypatch):
        """Test list with empty cache in JSON mode."""
        # Mock cache
        mock_cache_instance = Mock()
        mock_cache_instance.list_all.return_value = {}
        monkeypatch.setattr("prime_uve.cli.list.Cache", lambda: mock_cache_instance)

        # Execute
        result = runner.invoke(cli, ["list", "--json"])

        # Assert
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["venvs"] == []
        assert data["summary"]["total"] == 0
        assert data["summary"]["valid"] == 0
        assert data["summary"]["orphaned"] == 0

    def test_list_single_valid_project(self, runner, tmp_path, monkeypatch):
        """Test list with one valid project."""
        # Setup
        project_path = tmp_path / "test_project"
        project_path.mkdir()

        venv_path = "${HOME}/prime-uve/venvs/test_abc123"
        env_file = project_path / ".env.uve"
        env_file.write_text(f"UV_PROJECT_ENVIRONMENT={venv_path}\n")

        # Mock cache
        mock_cache_instance = Mock()
        mock_cache_instance.list_all.return_value = {
            str(project_path): {
                "venv_path": venv_path,
                "project_name": "test_project",
                "path_hash": "abc123",
                "created_at": "2025-12-01T10:00:00Z",
            }
        }
        monkeypatch.setattr("prime_uve.cli.list.Cache", lambda: mock_cache_instance)

        # Execute
        result = runner.invoke(cli, ["list"])

        # Assert
        assert result.exit_code == 0
        assert "test_project" in result.output
        assert "[OK]" in result.output or "Valid" in result.output
        assert "Summary: 1 total, 1 valid, 0 orphaned" in result.output

    def test_list_multiple_projects(self, runner, tmp_path, monkeypatch):
        """Test list with multiple projects (mix of valid and orphaned)."""
        # Setup valid project
        valid_project = tmp_path / "valid_project"
        valid_project.mkdir()
        valid_venv = "${HOME}/prime-uve/venvs/valid_abc123"
        (valid_project / ".env.uve").write_text(
            f"UV_PROJECT_ENVIRONMENT={valid_venv}\n"
        )

        # Setup orphan project (no .env.uve)
        orphan_project = tmp_path / "orphan_project"
        orphan_project.mkdir()

        # Mock cache
        mock_cache_instance = Mock()
        mock_cache_instance.list_all.return_value = {
            str(valid_project): {
                "venv_path": valid_venv,
                "project_name": "valid_project",
                "path_hash": "abc123",
                "created_at": "2025-12-01T10:00:00Z",
            },
            str(orphan_project): {
                "venv_path": "${HOME}/prime-uve/venvs/orphan_def456",
                "project_name": "orphan_project",
                "path_hash": "def456",
                "created_at": "2025-12-02T11:00:00Z",
            },
        }
        monkeypatch.setattr("prime_uve.cli.list.Cache", lambda: mock_cache_instance)

        # Execute
        result = runner.invoke(cli, ["list"])

        # Assert
        assert result.exit_code == 0
        assert "valid_project" in result.output
        assert "orphan_project" in result.output
        assert "Summary: 2 total, 1 valid, 1 orphaned" in result.output
        assert "prime-uve prune --orphan" in result.output

    def test_list_orphan_only_filter(self, runner, tmp_path, monkeypatch):
        """Test --orphan-only shows only orphaned entries."""
        # Setup
        valid_project = tmp_path / "valid"
        valid_project.mkdir()
        valid_venv = "${HOME}/prime-uve/venvs/valid_abc"
        (valid_project / ".env.uve").write_text(f"UV_PROJECT_ENVIRONMENT={valid_venv}\n")

        orphan_project = tmp_path / "orphan"
        orphan_project.mkdir()

        # Mock cache
        mock_cache_instance = Mock()
        mock_cache_instance.list_all.return_value = {
            str(valid_project): {
                "venv_path": valid_venv,
                "project_name": "valid",
                "path_hash": "abc",
                "created_at": "2025-12-01T10:00:00Z",
            },
            str(orphan_project): {
                "venv_path": "${HOME}/prime-uve/venvs/orphan_def",
                "project_name": "orphan",
                "path_hash": "def",
                "created_at": "2025-12-02T11:00:00Z",
            },
        }
        monkeypatch.setattr("prime_uve.cli.list.Cache", lambda: mock_cache_instance)

        # Execute
        result = runner.invoke(cli, ["list", "--orphan-only"])

        # Assert
        assert result.exit_code == 0
        assert "orphan" in result.output
        assert "valid" not in result.output.lower() or "Valid" not in result.output

    def test_list_orphan_only_no_orphans(self, runner, tmp_path, monkeypatch):
        """Test --orphan-only with no orphans shows message."""
        # Setup valid project
        project = tmp_path / "test"
        project.mkdir()
        venv = "${HOME}/prime-uve/venvs/test_abc"
        (project / ".env.uve").write_text(f"UV_PROJECT_ENVIRONMENT={venv}\n")

        # Mock cache
        mock_cache_instance = Mock()
        mock_cache_instance.list_all.return_value = {
            str(project): {
                "venv_path": venv,
                "project_name": "test",
                "path_hash": "abc",
                "created_at": "2025-12-01T10:00:00Z",
            }
        }
        monkeypatch.setattr("prime_uve.cli.list.Cache", lambda: mock_cache_instance)

        # Execute
        result = runner.invoke(cli, ["list", "--orphan-only"])

        # Assert
        assert result.exit_code == 0
        assert "No orphaned venvs found" in result.output

    def test_list_verbose_mode(self, runner, tmp_path, monkeypatch):
        """Test --verbose shows extended information."""
        # Setup
        project = tmp_path / "test"
        project.mkdir()
        venv = "${HOME}/prime-uve/venvs/test_abc123"
        (project / ".env.uve").write_text(f"UV_PROJECT_ENVIRONMENT={venv}\n")

        # Mock cache
        mock_cache_instance = Mock()
        mock_cache_instance.list_all.return_value = {
            str(project): {
                "venv_path": venv,
                "project_name": "test",
                "path_hash": "abc123",
                "created_at": "2025-12-01T10:00:00Z",
            }
        }
        monkeypatch.setattr("prime_uve.cli.list.Cache", lambda: mock_cache_instance)

        # Execute
        result = runner.invoke(cli, ["list", "--verbose"])

        # Assert
        assert result.exit_code == 0
        assert "Hash:" in result.output
        assert "Created:" in result.output
        assert "abc123" in result.output

    def test_list_json_output(self, runner, tmp_path, monkeypatch):
        """Test --json outputs valid JSON."""
        # Setup
        project = tmp_path / "test"
        project.mkdir()
        venv = "${HOME}/prime-uve/venvs/test_abc"
        (project / ".env.uve").write_text(f"UV_PROJECT_ENVIRONMENT={venv}\n")

        # Mock cache
        mock_cache_instance = Mock()
        mock_cache_instance.list_all.return_value = {
            str(project): {
                "venv_path": venv,
                "project_name": "test",
                "path_hash": "abc",
                "created_at": "2025-12-01T10:00:00Z",
            }
        }
        monkeypatch.setattr("prime_uve.cli.list.Cache", lambda: mock_cache_instance)

        # Execute
        result = runner.invoke(cli, ["list", "--json"])

        # Assert
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data["venvs"]) == 1
        assert data["venvs"][0]["project_name"] == "test"
        assert data["venvs"][0]["status"] == "valid"
        assert data["venvs"][0]["cache_matches_env"] is True
        assert data["summary"]["total"] == 1
        assert data["summary"]["valid"] == 1
        assert data["summary"]["orphaned"] == 0

    def test_list_table_formatting(self, runner, tmp_path, monkeypatch):
        """Test table column alignment and formatting."""
        # Setup
        project = tmp_path / "myproject"
        project.mkdir()
        venv = "${HOME}/prime-uve/venvs/myproject_abc"
        (project / ".env.uve").write_text(f"UV_PROJECT_ENVIRONMENT={venv}\n")

        mock_cache_instance = Mock()
        mock_cache_instance.list_all.return_value = {
            str(project): {
                "venv_path": venv,
                "project_name": "myproject",
                "path_hash": "abc",
                "created_at": "2025-12-01T10:00:00Z",
            }
        }
        monkeypatch.setattr("prime_uve.cli.list.Cache", lambda: mock_cache_instance)

        # Execute
        result = runner.invoke(cli, ["list"])

        # Assert
        assert result.exit_code == 0
        assert "PROJECT" in result.output
        assert "VENV PATH" in result.output
        assert "STATUS" in result.output
        assert "---" in result.output  # Separator line
