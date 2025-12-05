"""Tests for the prune command."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from prime_uve.cli.prune import (
    format_bytes,
    get_disk_usage,
    is_orphaned,
    remove_venv_directory,
)
from prime_uve.cli.main import cli


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture(autouse=True)
def mock_venv_base_dir_global(tmp_path):
    """Automatically mock get_venv_base_dir to use temp directory for all tests.

    This prevents tests from accidentally accessing or deleting real venvs.
    """
    test_venv_dir = tmp_path / ".prime-uve" / "venvs"
    test_venv_dir.mkdir(parents=True, exist_ok=True)

    # Patch get_venv_base_dir to return test directory
    with patch("prime_uve.cli.prune.get_venv_base_dir", return_value=test_venv_dir):
        yield test_venv_dir


@pytest.fixture
def mock_cache(tmp_path):
    """Mock cache with test data."""
    cache_data = {
        str(tmp_path / "project1"): {
            "venv_path": "${HOME}/.prime-uve/venvs/project1_abc123",
            "project_name": "project1",
            "path_hash": "abc123",
            "created_at": "2025-12-01T10:00:00Z",
        },
        str(tmp_path / "project2"): {
            "venv_path": "${HOME}/.prime-uve/venvs/project2_def456",
            "project_name": "project2",
            "path_hash": "def456",
            "created_at": "2025-12-02T11:00:00Z",
        },
    }
    return cache_data


@pytest.fixture
def venv_dir(tmp_path):
    """Create a test venv directory structure."""
    venv_base = tmp_path / "venvs"
    venv_base.mkdir()

    # Create some test venv directories with files
    venv1 = venv_base / "project1_abc123"
    venv1.mkdir()
    (venv1 / "bin").mkdir()
    (venv1 / "bin" / "python").write_text("#!/usr/bin/env python")

    venv2 = venv_base / "project2_def456"
    venv2.mkdir()
    (venv2 / "lib").mkdir()
    (venv2 / "lib" / "site.py").write_text("# site packages")

    return venv_base


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_format_bytes_zero(self):
        """Test formatting zero bytes."""
        assert format_bytes(0) == "0 B"

    def test_format_bytes_small(self):
        """Test formatting small byte values."""
        assert format_bytes(100) == "100 B"
        assert format_bytes(1023) == "1023 B"

    def test_format_bytes_kb(self):
        """Test formatting kilobytes."""
        assert format_bytes(1024) == "1.0 KB"
        assert format_bytes(1536) == "1.5 KB"

    def test_format_bytes_mb(self):
        """Test formatting megabytes."""
        assert format_bytes(1024 * 1024) == "1.0 MB"
        assert format_bytes(int(125.5 * 1024 * 1024)) == "125.5 MB"

    def test_format_bytes_gb(self):
        """Test formatting gigabytes."""
        assert format_bytes(1024 * 1024 * 1024) == "1.0 GB"
        assert format_bytes(int(2.5 * 1024 * 1024 * 1024)) == "2.5 GB"

    def test_get_disk_usage_empty_dir(self, tmp_path):
        """Test disk usage calculation for empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        assert get_disk_usage(empty_dir) == 0

    def test_get_disk_usage_with_files(self, tmp_path):
        """Test disk usage calculation with files."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        (test_dir / "file1.txt").write_text("a" * 100)
        (test_dir / "file2.txt").write_text("b" * 200)
        usage = get_disk_usage(test_dir)
        assert usage >= 300  # At least the file content size

    def test_get_disk_usage_nonexistent(self, tmp_path):
        """Test disk usage for nonexistent directory."""
        nonexistent = tmp_path / "nonexistent"
        assert get_disk_usage(nonexistent) == 0

    def test_is_orphaned_missing_env_file(self, tmp_path):
        """Test orphaned detection when .env.uve is missing."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        cache_entry = {
            "venv_path": "${HOME}/.prime-uve/venvs/project_abc123",
            "project_name": "project",
        }

        assert is_orphaned(str(project_path), cache_entry) is True

    def test_is_orphaned_mismatched_path(self, tmp_path):
        """Test orphaned detection when paths don't match."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        env_file = project_path / ".env.uve"
        env_file.write_text(
            "UV_PROJECT_ENVIRONMENT=${HOME}/.prime-uve/venvs/different_xyz789\n"
        )

        cache_entry = {
            "venv_path": "${HOME}/.prime-uve/venvs/project_abc123",
            "project_name": "project",
        }

        assert is_orphaned(str(project_path), cache_entry) is True

    def test_is_orphaned_matching_path(self, tmp_path):
        """Test orphaned detection when paths match (not orphaned)."""
        project_path = tmp_path / "project"
        project_path.mkdir()

        venv_path = "${HOME}/.prime-uve/venvs/project_abc123"
        env_file = project_path / ".env.uve"
        env_file.write_text(f"UV_PROJECT_ENVIRONMENT={venv_path}\n")

        cache_entry = {
            "venv_path": venv_path,
            "project_name": "project",
        }

        assert is_orphaned(str(project_path), cache_entry) is False

    def test_remove_venv_directory_success(self, tmp_path):
        """Test successful venv removal."""
        venv_dir = tmp_path / "test_venv"
        venv_dir.mkdir()
        (venv_dir / "file.txt").write_text("test")

        success, error = remove_venv_directory(str(venv_dir), dry_run=False)

        assert success is True
        assert error is None
        assert not venv_dir.exists()

    def test_remove_venv_directory_dry_run(self, tmp_path):
        """Test venv removal in dry run mode."""
        venv_dir = tmp_path / "test_venv"
        venv_dir.mkdir()
        (venv_dir / "file.txt").write_text("test")

        success, error = remove_venv_directory(str(venv_dir), dry_run=True)

        assert success is True
        assert error is None
        assert venv_dir.exists()  # Should still exist

    def test_remove_venv_directory_nonexistent(self, tmp_path):
        """Test removing nonexistent venv (should succeed)."""
        nonexistent = tmp_path / "nonexistent"

        success, error = remove_venv_directory(str(nonexistent), dry_run=False)

        assert success is True
        assert error is None


class TestPruneCommand:
    """Tests for prune_command function."""

    def test_prune_command_no_mode(self, runner):
        """Test prune command without specifying a mode."""
        result = runner.invoke(cli, ["prune"])

        assert result.exit_code == 1
        assert "Must specify one mode" in result.output

    def test_prune_command_multiple_modes(self, runner):
        """Test prune command with multiple modes."""
        result = runner.invoke(cli, ["prune", "--all", "--orphan"])

        assert result.exit_code == 1
        assert "Cannot specify multiple modes" in result.output

    def test_prune_command_all_valid_combination(self, runner):
        """Test prune command with --all and --valid combination."""
        result = runner.invoke(cli, ["prune", "--all", "--valid"])

        assert result.exit_code == 1
        assert "Cannot specify multiple modes" in result.output

    def test_prune_command_valid_orphan_combination(self, runner):
        """Test prune command with --valid and --orphan combination."""
        result = runner.invoke(cli, ["prune", "--valid", "--orphan"])

        assert result.exit_code == 1
        assert "Cannot specify multiple modes" in result.output

    @patch("prime_uve.cli.prune.Cache")
    def test_prune_command_all_dry_run(self, mock_cache_class, runner, tmp_path):
        """Test prune --all in dry run mode."""
        # Setup mock cache
        mock_cache = Mock()
        mock_cache.list_all.return_value = {
            str(tmp_path / "project1"): {
                "venv_path": "${HOME}/.prime-uve/venvs/project1_abc123",
                "project_name": "project1",
                "path_hash": "abc123",
                "created_at": "2025-12-01T10:00:00Z",
            }
        }
        mock_cache_class.return_value = mock_cache

        result = runner.invoke(cli, ["prune", "--all", "--dry-run", "--yes"])

        assert result.exit_code == 0
        assert "[DRY RUN]" in result.output
        mock_cache.clear.assert_not_called()  # Should not clear in dry run

    @patch("prime_uve.cli.prune.scan_venv_directory")
    @patch("prime_uve.cli.prune.Cache")
    def test_prune_command_orphan_json_output(
        self, mock_cache_class, mock_scan, runner, tmp_path
    ):
        """Test prune --orphan with JSON output."""
        # Setup mock cache
        mock_cache = Mock()
        mock_cache.list_all.return_value = {}
        mock_cache_class.return_value = mock_cache
        # Mock scan_venv_directory to return no venvs
        mock_scan.return_value = []

        result = runner.invoke(cli, ["prune", "--orphan", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "removed" in data
        assert "failed" in data
        assert data["removed"] == []


class TestPruneAll:
    """Tests for prune_all function."""

    @patch("prime_uve.cli.prune.auto_register_current_project")
    @patch("prime_uve.cli.prune.find_untracked_venvs")
    @patch("prime_uve.cli.prune.Cache")
    def test_prune_all_empty_cache(self, mock_cache_class, mock_find_untracked, mock_auto_register, runner):
        """Test prune --all with empty cache and no untracked venvs."""
        mock_cache = Mock()
        mock_cache.list_all.return_value = {}
        mock_cache_class.return_value = mock_cache
        mock_find_untracked.return_value = []  # No untracked venvs

        result = runner.invoke(cli, ["prune", "--all"], input="yes\n")

        assert result.exit_code == 0
        assert "No managed venvs found" in result.output

    @patch("prime_uve.cli.prune.Cache")
    @patch("prime_uve.cli.prune.expand_path_variables")
    @patch("prime_uve.cli.prune.get_disk_usage")
    def test_prune_all_with_venvs(
        self, mock_disk_usage, mock_expand, mock_cache_class, runner, tmp_path
    ):
        """Test prune --all with venvs."""
        # Setup mocks
        venv1 = tmp_path / "venv1"
        venv1.mkdir()

        mock_cache = Mock()
        mock_cache.list_all.return_value = {
            str(tmp_path / "project1"): {
                "venv_path": "${HOME}/venvs/project1",
                "project_name": "project1",
                "path_hash": "abc123",
                "created_at": "2025-12-01T10:00:00Z",
            }
        }
        mock_cache_class.return_value = mock_cache
        mock_expand.return_value = venv1
        mock_disk_usage.return_value = 1024

        result = runner.invoke(cli, ["prune", "--all"], input="yes\n")

        assert result.exit_code == 0
        mock_cache.clear.assert_called_once()
        assert not venv1.exists()  # Should be removed

    @patch("prime_uve.cli.prune.Cache")
    def test_prune_all_user_abort(self, mock_cache_class, runner, tmp_path):
        """Test prune --all when user aborts."""
        mock_cache = Mock()
        mock_cache.list_all.return_value = {
            str(tmp_path / "project1"): {
                "venv_path": "${HOME}/venvs/project1",
                "project_name": "project1",
                "path_hash": "abc123",
                "created_at": "2025-12-01T10:00:00Z",
            }
        }
        mock_cache_class.return_value = mock_cache

        result = runner.invoke(cli, ["prune", "--all"], input="no\n")

        assert result.exit_code == 0
        assert "Aborted" in result.output
        mock_cache.clear.assert_not_called()

    @patch("prime_uve.cli.prune.auto_register_current_project")
    @patch("prime_uve.cli.prune.find_untracked_venvs")
    @patch("prime_uve.cli.prune.expand_path_variables")
    @patch("prime_uve.cli.prune.Cache")
    def test_prune_all_removes_untracked_venvs(
        self, mock_cache_class, mock_expand, mock_find_untracked, mock_auto_register, runner, tmp_path
    ):
        """Test that --all removes untracked venvs on disk."""
        venv1 = tmp_path / "venv1"
        venv1.mkdir()
        untracked_venv = tmp_path / "untracked_venv"
        untracked_venv.mkdir()

        mock_cache = Mock()
        mock_cache.list_all.return_value = {
            str(tmp_path / "project1"): {
                "venv_path": "${HOME}/venvs/project1",
                "project_name": "project1",
                "path_hash": "abc123",
                "created_at": "2025-12-01T10:00:00Z",
            }
        }
        mock_cache_class.return_value = mock_cache
        mock_expand.return_value = venv1
        mock_find_untracked.return_value = [
            {
                "project_name": "<unknown: orphan>",
                "venv_path": None,
                "venv_path_expanded": untracked_venv,
                "size": 512,
            }
        ]

        result = runner.invoke(cli, ["prune", "--all"], input="yes\n")

        assert result.exit_code == 0
        assert "untracked" in result.output or "2 venv" in result.output
        assert not venv1.exists()  # Cached venv removed
        assert not untracked_venv.exists()  # Untracked venv removed

    @patch("prime_uve.cli.prune.auto_register_current_project")
    @patch("prime_uve.cli.prune.Cache")
    def test_prune_all_respects_yes_flag(
        self, mock_cache_class, mock_auto_register, runner, tmp_path
    ):
        """Test that --all respects --yes flag to skip confirmation."""
        mock_cache = Mock()
        mock_cache.list_all.return_value = {
            str(tmp_path / "project1"): {
                "venv_path": "${HOME}/venvs/project1",
                "project_name": "project1",
                "path_hash": "abc123",
                "created_at": "2025-12-01T10:00:00Z",
            }
        }
        mock_cache_class.return_value = mock_cache

        # Test that --yes flag skips confirmation
        result = runner.invoke(cli, ["prune", "--all", "--yes"])

        # Should succeed without prompting
        assert result.exit_code == 0

    @patch("prime_uve.cli.prune.auto_register_current_project")
    @patch("prime_uve.cli.prune.Cache")
    def test_prune_all_dry_run(self, mock_cache_class, mock_auto_register, runner, tmp_path):
        """Test prune --all in dry run mode."""
        mock_cache = Mock()
        mock_cache.list_all.return_value = {
            str(tmp_path / "project1"): {
                "venv_path": "${HOME}/venvs/project1",
                "project_name": "project1",
                "path_hash": "abc123",
                "created_at": "2025-12-01T10:00:00Z",
            }
        }
        mock_cache_class.return_value = mock_cache

        result = runner.invoke(cli, ["prune", "--all", "--dry-run"])

        assert result.exit_code == 0
        assert "[DRY RUN]" in result.output
        mock_cache.clear.assert_not_called()  # Should not clear in dry run


class TestPruneValid:
    """Tests for prune_valid function."""

    @patch("prime_uve.cli.prune.Cache")
    def test_prune_valid_empty_cache(self, mock_cache_class, runner):
        """Test prune --valid with empty cache."""
        mock_cache = Mock()
        mock_cache.list_all.return_value = {}
        mock_cache_class.return_value = mock_cache

        result = runner.invoke(cli, ["prune", "--valid", "--yes"])

        assert result.exit_code == 0
        assert "No valid venvs found" in result.output or "No managed venvs found" in result.output

    @patch("prime_uve.cli.prune.Cache")
    @patch("prime_uve.cli.prune.expand_path_variables")
    @patch("prime_uve.cli.prune.get_disk_usage")
    def test_prune_valid_removes_only_valid_venvs(
        self, mock_disk_usage, mock_expand, mock_cache_class, runner, tmp_path
    ):
        """Test that --valid removes only valid venvs."""
        # Create project with valid .env.uve
        valid_project = tmp_path / "valid_project"
        valid_project.mkdir()
        venv_path = "${HOME}/.prime-uve/venvs/valid_project_abc123"
        env_file = valid_project / ".env.uve"
        env_file.write_text(f"UV_PROJECT_ENVIRONMENT={venv_path}\n")

        # Create project with orphaned .env.uve
        orphan_project = tmp_path / "orphan_project"
        orphan_project.mkdir()
        orphan_env_file = orphan_project / ".env.uve"
        orphan_env_file.write_text("UV_PROJECT_ENVIRONMENT=${HOME}/different/path\n")

        venv1 = tmp_path / "venv1"
        venv1.mkdir()
        venv2 = tmp_path / "venv2"
        venv2.mkdir()

        mock_cache = Mock()
        mock_cache.list_all.return_value = {
            str(valid_project): {
                "venv_path": venv_path,
                "project_name": "valid_project",
                "path_hash": "abc123",
                "created_at": "2025-12-01T10:00:00Z",
            },
            str(orphan_project): {
                "venv_path": "${HOME}/.prime-uve/venvs/orphan_project_def456",
                "project_name": "orphan_project",
                "path_hash": "def456",
                "created_at": "2025-12-02T11:00:00Z",
            }
        }
        mock_cache_class.return_value = mock_cache

        # Mock expand to return our test venvs
        def expand_side_effect(path):
            if "valid" in path:
                return venv1
            else:
                return venv2

        mock_expand.side_effect = expand_side_effect
        mock_disk_usage.return_value = 1024

        result = runner.invoke(cli, ["prune", "--valid", "--yes"])

        assert result.exit_code == 0
        # Only valid venv should be removed
        assert not venv1.exists()  # Valid venv removed
        assert venv2.exists()  # Orphaned venv NOT removed
        # Cache should have mapping removed for valid project only
        mock_cache.remove_mapping.assert_called_once()

    @patch("prime_uve.cli.prune.auto_register_current_project")
    @patch("prime_uve.cli.prune.Cache")
    @patch("prime_uve.cli.prune.expand_path_variables")
    @patch("prime_uve.cli.prune.get_disk_usage")
    def test_prune_valid_clears_cache_entries(
        self, mock_disk_usage, mock_expand, mock_cache_class, mock_auto_register, runner, tmp_path
    ):
        """Test that --valid clears cache entries for removed venvs."""
        # Create valid project
        valid_project = tmp_path / "valid_project"
        valid_project.mkdir()
        venv_path = "${HOME}/.prime-uve/venvs/valid_project_abc123"
        env_file = valid_project / ".env.uve"
        env_file.write_text(f"UV_PROJECT_ENVIRONMENT={venv_path}\n")

        venv_dir = tmp_path / "venv"
        venv_dir.mkdir()

        mock_cache = Mock()
        mock_cache.list_all.return_value = {
            str(valid_project): {
                "venv_path": venv_path,
                "project_name": "valid_project",
                "path_hash": "abc123",
                "created_at": "2025-12-01T10:00:00Z",
            }
        }
        mock_cache_class.return_value = mock_cache
        mock_expand.return_value = venv_dir
        mock_disk_usage.return_value = 1024

        result = runner.invoke(cli, ["prune", "--valid", "--yes"])

        assert result.exit_code == 0
        # Verify cache.remove_mapping was called with the project path
        mock_cache.remove_mapping.assert_called_once_with(Path(str(valid_project)))

    @patch("prime_uve.cli.prune.auto_register_current_project")
    @patch("prime_uve.cli.prune.Cache")
    def test_prune_valid_respects_yes_flag(self, mock_cache_class, mock_auto_register, runner, tmp_path):
        """Test that --valid respects --yes flag to skip confirmation."""
        valid_project = tmp_path / "valid_project"
        valid_project.mkdir()
        venv_path = "${HOME}/.prime-uve/venvs/valid_project_abc123"
        env_file = valid_project / ".env.uve"
        env_file.write_text(f"UV_PROJECT_ENVIRONMENT={venv_path}\n")

        venv_dir = tmp_path / "venv"
        venv_dir.mkdir()

        mock_cache = Mock()
        mock_cache.list_all.return_value = {
            str(valid_project): {
                "venv_path": venv_path,
                "project_name": "valid_project",
                "path_hash": "abc123",
                "created_at": "2025-12-01T10:00:00Z",
            }
        }
        mock_cache_class.return_value = mock_cache

        result = runner.invoke(cli, ["prune", "--valid", "--yes"])

        # Should succeed without prompting
        assert result.exit_code == 0

    @patch("prime_uve.cli.prune.auto_register_current_project")
    @patch("prime_uve.cli.prune.Cache")
    def test_prune_valid_dry_run(self, mock_cache_class, mock_auto_register, runner, tmp_path):
        """Test prune --valid in dry run mode."""
        valid_project = tmp_path / "valid_project"
        valid_project.mkdir()
        venv_path = "${HOME}/.prime-uve/venvs/valid_project_abc123"
        env_file = valid_project / ".env.uve"
        env_file.write_text(f"UV_PROJECT_ENVIRONMENT={venv_path}\n")

        venv_dir = tmp_path / "venv"
        venv_dir.mkdir()

        mock_cache = Mock()
        mock_cache.list_all.return_value = {
            str(valid_project): {
                "venv_path": venv_path,
                "project_name": "valid_project",
                "path_hash": "abc123",
                "created_at": "2025-12-01T10:00:00Z",
            }
        }
        mock_cache_class.return_value = mock_cache

        result = runner.invoke(cli, ["prune", "--valid", "--dry-run"])

        assert result.exit_code == 0
        assert "[DRY RUN]" in result.output
        mock_cache.remove_mapping.assert_not_called()  # Should not modify cache


class TestPruneOrphan:
    """Tests for prune_orphan function."""

    @patch("prime_uve.cli.prune.scan_venv_directory")
    @patch("prime_uve.cli.prune.Cache")
    def test_prune_orphan_no_orphans(
        self, mock_cache_class, mock_scan, runner, tmp_path
    ):
        """Test prune --orphan with no orphaned venvs."""
        project_path = tmp_path / "project1"
        project_path.mkdir()

        venv_path = "${HOME}/.prime-uve/venvs/project1_abc123"
        env_file = project_path / ".env.uve"
        env_file.write_text(f"UV_PROJECT_ENVIRONMENT={venv_path}\n")

        mock_cache = Mock()
        mock_cache.list_all.return_value = {
            str(project_path): {
                "venv_path": venv_path,
                "project_name": "project1",
                "path_hash": "abc123",
                "created_at": "2025-12-01T10:00:00Z",
            }
        }
        mock_cache_class.return_value = mock_cache
        # Mock scan to return no untracked venvs
        mock_scan.return_value = []

        result = runner.invoke(cli, ["prune", "--orphan", "--yes"])

        assert result.exit_code == 0
        assert "No orphaned venvs found" in result.output

    @patch("prime_uve.cli.prune.scan_venv_directory")
    @patch("prime_uve.cli.prune.Cache")
    @patch("prime_uve.cli.prune.expand_path_variables")
    @patch("prime_uve.cli.prune.get_disk_usage")
    def test_prune_orphan_with_orphans(
        self,
        mock_disk_usage,
        mock_expand,
        mock_cache_class,
        mock_scan,
        runner,
        tmp_path,
    ):
        """Test prune --orphan with orphaned venvs."""
        project_path = tmp_path / "project1"
        project_path.mkdir()

        # Create .env.uve with different path (orphan)
        env_file = project_path / ".env.uve"
        env_file.write_text("UV_PROJECT_ENVIRONMENT=${HOME}/different/path\n")

        venv1 = tmp_path / "venv1"
        venv1.mkdir()

        mock_cache = Mock()
        mock_cache.list_all.return_value = {
            str(project_path): {
                "venv_path": "${HOME}/venvs/project1",
                "project_name": "project1",
                "path_hash": "abc123",
                "created_at": "2025-12-01T10:00:00Z",
            }
        }
        mock_cache_class.return_value = mock_cache
        mock_expand.return_value = venv1
        mock_disk_usage.return_value = 1024
        # Mock scan to return no untracked venvs
        mock_scan.return_value = []

        result = runner.invoke(cli, ["prune", "--orphan", "--yes"])

        assert result.exit_code == 0
        assert "orphaned venv(s)" in result.output
        mock_cache.remove_mapping.assert_called_once()


class TestPruneCurrent:
    """Tests for prune_current function."""

    @patch("prime_uve.cli.prune.find_project_root")
    def test_prune_current_not_in_project(self, mock_find_root, runner):
        """Test prune --current when not in a project."""
        mock_find_root.return_value = None

        result = runner.invoke(cli, ["prune", "--current"])

        assert result.exit_code == 1
        assert "Not in a Python project" in result.output

    @patch("prime_uve.cli.prune.find_project_root")
    @patch("prime_uve.cli.prune.Cache")
    def test_prune_current_not_managed(
        self, mock_cache_class, mock_find_root, runner, tmp_path
    ):
        """Test prune --current when project not managed."""
        mock_find_root.return_value = tmp_path
        mock_cache = Mock()
        mock_cache.get_mapping.return_value = None
        mock_cache_class.return_value = mock_cache

        result = runner.invoke(cli, ["prune", "--current"])

        assert result.exit_code == 1
        assert "not managed by prime-uve" in result.output

    @patch("prime_uve.cli.prune.find_project_root")
    @patch("prime_uve.cli.prune.Cache")
    @patch("prime_uve.cli.prune.expand_path_variables")
    @patch("prime_uve.cli.prune.get_disk_usage")
    def test_prune_current_success(
        self,
        mock_disk_usage,
        mock_expand,
        mock_cache_class,
        mock_find_root,
        runner,
        tmp_path,
    ):
        """Test successful prune --current."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        venv_dir = tmp_path / "venv"
        venv_dir.mkdir()

        # Create pyproject.toml so find_env_file works
        (project_root / "pyproject.toml").write_text(
            "[project]\nname = 'test-project'\n"
        )
        # Create .env.uve file
        env_file = project_root / ".env.uve"
        env_file.write_text("UV_PROJECT_ENVIRONMENT=${HOME}/venv\n")

        mock_find_root.return_value = project_root
        mock_cache = Mock()
        mock_cache.get_mapping.return_value = {
            "venv_path": "${HOME}/venv",
            "project_name": "test-project",
            "path_hash": "abc123",
        }
        mock_cache_class.return_value = mock_cache
        mock_expand.return_value = venv_dir
        mock_disk_usage.return_value = 1024

        # Change to project directory so find_env_file works
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(project_root)
            result = runner.invoke(cli, ["prune", "--current", "--yes"])
        finally:
            os.chdir(original_cwd)

        assert result.exit_code == 0
        mock_cache.remove_mapping.assert_called_once_with(project_root)
        assert not venv_dir.exists()
        # Check that .env.uve was cleared
        assert env_file.read_text().strip() == ""


class TestPrunePath:
    """Tests for prune_path function."""

    @patch("prime_uve.cli.prune.get_venv_base_dir")
    def test_prune_path_outside_base_dir(self, mock_get_base, runner, tmp_path):
        """Test prune with path outside venv base directory."""
        mock_get_base.return_value = tmp_path / "prime-uve" / "venvs"
        bad_path = tmp_path / "other" / "path"

        result = runner.invoke(cli, ["prune", str(bad_path)])

        assert result.exit_code == 1
        assert "must be within" in result.output

    @patch("prime_uve.cli.prune.get_venv_base_dir")
    def test_prune_path_nonexistent(self, mock_get_base, runner, tmp_path):
        """Test prune with nonexistent path."""
        venv_base = tmp_path / "prime-uve" / "venvs"
        venv_base.mkdir(parents=True)
        mock_get_base.return_value = venv_base

        nonexistent = venv_base / "nonexistent"

        result = runner.invoke(cli, ["prune", str(nonexistent)])

        assert result.exit_code == 1
        assert "does not exist" in result.output

    @patch("prime_uve.cli.prune.get_venv_base_dir")
    @patch("prime_uve.cli.prune.get_disk_usage")
    @patch("prime_uve.cli.prune.Cache")
    def test_prune_path_success(
        self, mock_cache_class, mock_disk_usage, mock_get_base, runner, tmp_path
    ):
        """Test successful path-based prune."""
        venv_base = tmp_path / "prime-uve" / "venvs"
        venv_base.mkdir(parents=True)
        venv_dir = venv_base / "test_venv"
        venv_dir.mkdir()

        mock_get_base.return_value = venv_base
        mock_disk_usage.return_value = 1024
        mock_cache = Mock()
        mock_cache.list_all.return_value = {}
        mock_cache_class.return_value = mock_cache

        result = runner.invoke(cli, ["prune", str(venv_dir), "--yes"])

        assert result.exit_code == 0
        assert not venv_dir.exists()
