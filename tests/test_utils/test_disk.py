"""Tests for disk usage utilities."""

import os
import tempfile
from pathlib import Path

import pytest

from prime_uve.utils.disk import format_bytes, get_disk_usage


class TestGetDiskUsage:
    """Tests for get_disk_usage function."""

    def test_empty_directory(self, tmp_path):
        """Test disk usage of empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        size = get_disk_usage(empty_dir)
        assert size == 0

    def test_single_file(self, tmp_path):
        """Test disk usage with single file."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        test_file = test_dir / "file.txt"
        content = "Hello, World!" * 100  # ~1300 bytes
        test_file.write_text(content)

        size = get_disk_usage(test_dir)
        expected_size = len(content.encode("utf-8"))
        assert size == expected_size

    def test_multiple_files(self, tmp_path):
        """Test disk usage with multiple files."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        # Create several files
        file1 = test_dir / "file1.txt"
        file1.write_text("A" * 1000)

        file2 = test_dir / "file2.txt"
        file2.write_text("B" * 2000)

        file3 = test_dir / "file3.txt"
        file3.write_text("C" * 3000)

        size = get_disk_usage(test_dir)
        assert size == 6000  # 1000 + 2000 + 3000

    def test_nested_directories(self, tmp_path):
        """Test disk usage with nested directory structure."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        # Create nested structure
        subdir1 = test_dir / "sub1"
        subdir1.mkdir()
        (subdir1 / "file1.txt").write_text("A" * 1000)

        subdir2 = subdir1 / "sub2"
        subdir2.mkdir()
        (subdir2 / "file2.txt").write_text("B" * 2000)

        # File in root
        (test_dir / "root.txt").write_text("C" * 500)

        size = get_disk_usage(test_dir)
        assert size == 3500  # 1000 + 2000 + 500

    def test_nonexistent_directory(self, tmp_path):
        """Test disk usage of non-existent directory."""
        nonexistent = tmp_path / "does_not_exist"
        size = get_disk_usage(nonexistent)
        assert size == 0

    def test_binary_files(self, tmp_path):
        """Test disk usage with binary files."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        # Create binary file
        binary_file = test_dir / "binary.dat"
        binary_data = bytes(range(256)) * 10  # 2560 bytes
        binary_file.write_bytes(binary_data)

        size = get_disk_usage(test_dir)
        assert size == 2560

    def test_matches_os_walk_and_rglob(self, tmp_path):
        """Verify os.walk implementation matches rglob behavior."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        # Create test structure
        (test_dir / "file1.txt").write_text("A" * 1000)
        subdir = test_dir / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("B" * 2000)

        # Calculate using our function (os.walk)
        size_os_walk = get_disk_usage(test_dir)

        # Calculate using rglob (old method)
        size_rglob = sum(
            f.stat().st_size for f in test_dir.rglob("*") if f.is_file()
        )

        assert size_os_walk == size_rglob == 3000


class TestFormatBytes:
    """Tests for format_bytes function."""

    def test_zero_bytes(self):
        """Test formatting zero bytes."""
        assert format_bytes(0) == "0 B"

    def test_bytes(self):
        """Test formatting bytes (< 1024)."""
        assert format_bytes(1) == "1 B"
        assert format_bytes(100) == "100 B"
        assert format_bytes(1023) == "1023 B"

    def test_kilobytes(self):
        """Test formatting kilobytes."""
        assert format_bytes(1024) == "1.0 KB"
        assert format_bytes(1536) == "1.5 KB"
        assert format_bytes(2048) == "2.0 KB"
        assert format_bytes(1024 * 10) == "10.0 KB"

    def test_megabytes(self):
        """Test formatting megabytes."""
        assert format_bytes(1024 * 1024) == "1.0 MB"
        assert format_bytes(1024 * 1024 * 1.5) == "1.5 MB"
        assert format_bytes(1024 * 1024 * 125) == "125.0 MB"

    def test_gigabytes(self):
        """Test formatting gigabytes."""
        assert format_bytes(1024 * 1024 * 1024) == "1.0 GB"
        assert format_bytes(1024 * 1024 * 1024 * 1.9) == "1.9 GB"
        assert format_bytes(1024 * 1024 * 1024 * 50) == "50.0 GB"

    def test_terabytes(self):
        """Test formatting terabytes."""
        assert format_bytes(1024 * 1024 * 1024 * 1024) == "1.0 TB"
        assert format_bytes(1024 * 1024 * 1024 * 1024 * 5) == "5.0 TB"

    def test_rounding(self):
        """Test decimal rounding."""
        # 1.46 KB should round to 1.5 KB
        assert format_bytes(1500) == "1.5 KB"
        # 1.44 KB should round to 1.4 KB
        assert format_bytes(1475) == "1.4 KB"

    def test_real_world_sizes(self):
        """Test with real-world venv sizes."""
        # Small venv: ~40 MB
        assert format_bytes(40_668_362) == "38.8 MB"

        # Medium venv: ~250 MB
        assert format_bytes(250_000_000) == "238.4 MB"

        # Large venv: ~1.9 GB (from benchmark)
        assert format_bytes(2_034_187_370) == "1.9 GB"
