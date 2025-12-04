"""Tests for cache system."""

import json
import multiprocessing
import sys
import time

import pytest

from prime_uve.core.cache import Cache, CacheError, ValidationResult
from prime_uve.core.paths import generate_hash, generate_venv_path, get_project_name


# ============================================================================
# Basic Operations Tests
# ============================================================================


def test_add_mapping(tmp_path):
    """Adding a mapping persists it."""
    cache_file = tmp_path / "cache.json"
    cache = Cache(cache_file)

    project_path = tmp_path / "my-project"
    project_path.mkdir()

    venv_path = generate_venv_path(project_path)
    project_name = get_project_name(project_path)
    path_hash = generate_hash(project_path)

    cache.add_mapping(
        project_path=project_path,
        venv_path=venv_path,
        project_name=project_name,
        path_hash=path_hash,
    )

    # Verify mapping was added
    mapping = cache.get_mapping(project_path)
    assert mapping is not None
    assert mapping["venv_path"] == venv_path
    assert mapping["project_name"] == project_name
    assert mapping["path_hash"] == path_hash
    assert "created_at" in mapping
    assert "last_validated" in mapping
    assert "venv_path_expanded" in mapping


def test_get_mapping(tmp_path):
    """Getting a mapping returns correct data."""
    cache_file = tmp_path / "cache.json"
    cache = Cache(cache_file)

    project_path = tmp_path / "test-project"
    project_path.mkdir()

    venv_path = generate_venv_path(project_path)
    project_name = get_project_name(project_path)
    path_hash = generate_hash(project_path)

    cache.add_mapping(project_path, venv_path, project_name, path_hash)

    mapping = cache.get_mapping(project_path)
    assert mapping["venv_path"] == venv_path
    assert mapping["project_name"] == project_name
    assert mapping["path_hash"] == path_hash


def test_get_mapping_not_found(tmp_path):
    """Getting non-existent mapping returns None."""
    cache_file = tmp_path / "cache.json"
    cache = Cache(cache_file)

    project_path = tmp_path / "nonexistent"
    mapping = cache.get_mapping(project_path)
    assert mapping is None


def test_remove_mapping(tmp_path):
    """Removing a mapping deletes it."""
    cache_file = tmp_path / "cache.json"
    cache = Cache(cache_file)

    project_path = tmp_path / "test-project"
    project_path.mkdir()

    venv_path = generate_venv_path(project_path)
    project_name = get_project_name(project_path)
    path_hash = generate_hash(project_path)

    cache.add_mapping(project_path, venv_path, project_name, path_hash)
    assert cache.get_mapping(project_path) is not None

    result = cache.remove_mapping(project_path)
    assert result is True
    assert cache.get_mapping(project_path) is None


def test_remove_mapping_not_found(tmp_path):
    """Removing non-existent mapping returns False."""
    cache_file = tmp_path / "cache.json"
    cache = Cache(cache_file)

    project_path = tmp_path / "nonexistent"
    result = cache.remove_mapping(project_path)
    assert result is False


def test_list_all_empty(tmp_path):
    """Empty cache returns empty dict."""
    cache_file = tmp_path / "cache.json"
    cache = Cache(cache_file)

    mappings = cache.list_all()
    assert mappings == {}


def test_list_all_multiple(tmp_path):
    """List all returns all mappings."""
    cache_file = tmp_path / "cache.json"
    cache = Cache(cache_file)

    # Add multiple mappings
    projects = []
    for i in range(3):
        project_path = tmp_path / f"project-{i}"
        project_path.mkdir()
        projects.append(project_path)

        venv_path = generate_venv_path(project_path)
        project_name = get_project_name(project_path)
        path_hash = generate_hash(project_path)

        cache.add_mapping(project_path, venv_path, project_name, path_hash)

    # Verify all mappings are returned
    mappings = cache.list_all()
    assert len(mappings) == 3

    for project_path in projects:
        assert str(project_path.resolve()) in mappings


def test_clear(tmp_path):
    """Clear removes all mappings."""
    cache_file = tmp_path / "cache.json"
    cache = Cache(cache_file)

    # Add some mappings
    for i in range(3):
        project_path = tmp_path / f"project-{i}"
        project_path.mkdir()

        venv_path = generate_venv_path(project_path)
        project_name = get_project_name(project_path)
        path_hash = generate_hash(project_path)

        cache.add_mapping(project_path, venv_path, project_name, path_hash)

    assert len(cache.list_all()) == 3

    # Clear cache
    cache.clear()
    assert cache.list_all() == {}


# ============================================================================
# Persistence Tests
# ============================================================================


def test_persistence_across_instances(tmp_path):
    """Mappings persist when cache is reloaded."""
    cache_file = tmp_path / "cache.json"
    cache1 = Cache(cache_file)

    project_path = tmp_path / "test-project"
    project_path.mkdir()

    venv_path = generate_venv_path(project_path)
    project_name = get_project_name(project_path)
    path_hash = generate_hash(project_path)

    cache1.add_mapping(project_path, venv_path, project_name, path_hash)

    # Create new cache instance
    cache2 = Cache(cache_file)
    mapping = cache2.get_mapping(project_path)

    assert mapping is not None
    assert mapping["venv_path"] == venv_path
    assert mapping["project_name"] == project_name


def test_cache_created_if_missing(tmp_path):
    """Cache file is created on first write."""
    cache_file = tmp_path / "cache.json"
    assert not cache_file.exists()

    cache = Cache(cache_file)
    project_path = tmp_path / "test-project"
    project_path.mkdir()

    venv_path = generate_venv_path(project_path)
    project_name = get_project_name(project_path)
    path_hash = generate_hash(project_path)

    cache.add_mapping(project_path, venv_path, project_name, path_hash)

    assert cache_file.exists()


def test_cache_directory_created(tmp_path):
    """Parent directory is created if missing."""
    cache_dir = tmp_path / "nested" / "deep"
    cache_file = cache_dir / "cache.json"
    assert not cache_dir.exists()

    cache = Cache(cache_file)
    project_path = tmp_path / "test-project"
    project_path.mkdir()

    venv_path = generate_venv_path(project_path)
    project_name = get_project_name(project_path)
    path_hash = generate_hash(project_path)

    cache.add_mapping(project_path, venv_path, project_name, path_hash)

    assert cache_dir.exists()
    assert cache_file.exists()


# ============================================================================
# Validation Tests
# ============================================================================


def test_validate_mapping_valid(tmp_path):
    """Validation passes when everything exists and matches."""
    cache_file = tmp_path / "cache.json"
    cache = Cache(cache_file)

    # Create project and venv directories
    project_path = tmp_path / "test-project"
    project_path.mkdir()

    venv_path = generate_venv_path(project_path)
    project_name = get_project_name(project_path)
    path_hash = generate_hash(project_path)

    # Expand venv path and create directory
    from prime_uve.core.paths import expand_path_variables

    venv_expanded = expand_path_variables(venv_path)
    venv_expanded.mkdir(parents=True)

    # Create .env.uve with matching path
    env_file = project_path / ".env.uve"
    env_file.write_text(f'UV_PROJECT_ENVIRONMENT="{venv_path}"')

    # Add mapping to cache
    cache.add_mapping(project_path, venv_path, project_name, path_hash)

    # Validate
    result = cache.validate_mapping(project_path)
    assert result.is_valid
    assert result.status == "valid"
    assert result.issues == []


def test_validate_mapping_project_missing(tmp_path):
    """Validation detects missing project directory."""
    cache_file = tmp_path / "cache.json"
    cache = Cache(cache_file)

    project_path = tmp_path / "test-project"
    project_path.mkdir()

    venv_path = generate_venv_path(project_path)
    project_name = get_project_name(project_path)
    path_hash = generate_hash(project_path)

    cache.add_mapping(project_path, venv_path, project_name, path_hash)

    # Delete project directory
    project_path.rmdir()

    # Validate
    result = cache.validate_mapping(project_path)
    assert result.is_orphaned
    assert result.status == "orphaned"
    assert "Project directory does not exist" in result.issues


def test_validate_mapping_venv_missing(tmp_path):
    """Validation detects missing venv directory."""
    cache_file = tmp_path / "cache.json"
    cache = Cache(cache_file)

    project_path = tmp_path / "test-project"
    project_path.mkdir()

    venv_path = generate_venv_path(project_path)
    project_name = get_project_name(project_path)
    path_hash = generate_hash(project_path)

    cache.add_mapping(project_path, venv_path, project_name, path_hash)

    # Validate (venv doesn't exist)
    result = cache.validate_mapping(project_path)
    assert result.is_orphaned
    assert result.status == "orphaned"
    assert any("Venv directory does not exist" in issue for issue in result.issues)


def test_validate_mapping_env_file_missing(tmp_path):
    """Validation detects missing .env.uve file."""
    cache_file = tmp_path / "cache.json"
    cache = Cache(cache_file)

    project_path = tmp_path / "test-project"
    project_path.mkdir()

    venv_path = generate_venv_path(project_path)
    project_name = get_project_name(project_path)
    path_hash = generate_hash(project_path)

    # Create venv directory
    from prime_uve.core.paths import expand_path_variables

    venv_expanded = expand_path_variables(venv_path)
    venv_expanded.mkdir(parents=True)

    cache.add_mapping(project_path, venv_path, project_name, path_hash)

    # Validate (.env.uve doesn't exist)
    result = cache.validate_mapping(project_path)
    assert result.is_orphaned
    assert result.status == "orphaned"
    assert any(".env.uve file does not exist" in issue for issue in result.issues)


def test_validate_mapping_path_mismatch(tmp_path):
    """Validation detects when .env.uve path differs from cache."""
    cache_file = tmp_path / "cache.json"
    cache = Cache(cache_file)

    project_path = tmp_path / "test-project"
    project_path.mkdir()

    venv_path = generate_venv_path(project_path)
    project_name = get_project_name(project_path)
    path_hash = generate_hash(project_path)

    # Create venv directory
    from prime_uve.core.paths import expand_path_variables

    venv_expanded = expand_path_variables(venv_path)
    venv_expanded.mkdir(parents=True)

    # Create .env.uve with DIFFERENT path
    env_file = project_path / ".env.uve"
    different_path = "${HOME}/prime-uve/venvs/different_path"
    env_file.write_text(f'UV_PROJECT_ENVIRONMENT="{different_path}"')

    cache.add_mapping(project_path, venv_path, project_name, path_hash)

    # Validate
    result = cache.validate_mapping(project_path)
    assert result.has_mismatch
    assert result.status == "mismatch"
    assert any("mismatch" in issue for issue in result.issues)


def test_validate_all(tmp_path):
    """Validate all returns results for all mappings."""
    cache_file = tmp_path / "cache.json"
    cache = Cache(cache_file)

    # Add multiple projects
    projects = []
    for i in range(3):
        project_path = tmp_path / f"project-{i}"
        project_path.mkdir()
        projects.append(project_path)

        venv_path = generate_venv_path(project_path)
        project_name = get_project_name(project_path)
        path_hash = generate_hash(project_path)

        cache.add_mapping(project_path, venv_path, project_name, path_hash)

    # Validate all
    results = cache.validate_all()
    assert len(results) == 3

    for project_path in projects:
        assert str(project_path.resolve()) in results
        assert isinstance(results[str(project_path.resolve())], ValidationResult)


def test_validation_updates_last_validated(tmp_path):
    """Validation updates last_validated timestamp."""
    cache_file = tmp_path / "cache.json"
    cache = Cache(cache_file)

    project_path = tmp_path / "test-project"
    project_path.mkdir()

    venv_path = generate_venv_path(project_path)
    project_name = get_project_name(project_path)
    path_hash = generate_hash(project_path)

    cache.add_mapping(project_path, venv_path, project_name, path_hash)

    # Get initial timestamp
    mapping1 = cache.get_mapping(project_path)
    timestamp1 = mapping1["last_validated"]

    # Wait a moment
    time.sleep(0.01)

    # Validate
    cache.validate_mapping(project_path)

    # Check timestamp was updated
    mapping2 = cache.get_mapping(project_path)
    timestamp2 = mapping2["last_validated"]

    assert timestamp2 > timestamp1


# ============================================================================
# Concurrency Tests
# ============================================================================


def _concurrent_writer(cache_path, project_path, index):
    """Helper function for concurrent write test."""
    cache = Cache(cache_path)
    venv_path = generate_venv_path(project_path)
    project_name = f"project-{index}"
    path_hash = generate_hash(project_path)

    cache.add_mapping(project_path, venv_path, project_name, path_hash)


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Multiprocessing concurrency test is flaky on Windows",
)
def test_concurrent_writes(tmp_path):
    """Multiple processes can write without corruption."""
    cache_file = tmp_path / "cache.json"

    # Create shared project paths
    projects = []
    for i in range(5):
        project_path = tmp_path / f"project-{i}"
        project_path.mkdir()
        projects.append(project_path)

    # Write concurrently from multiple processes
    processes = []
    for i, project_path in enumerate(projects):
        p = multiprocessing.Process(
            target=_concurrent_writer, args=(cache_file, project_path, i)
        )
        processes.append(p)
        p.start()

    # Wait for all processes to complete
    for p in processes:
        p.join()

    # Verify all mappings were written
    cache = Cache(cache_file)
    mappings = cache.list_all()
    assert len(mappings) == 5

    # Verify cache file is valid JSON
    with open(cache_file) as f:
        data = json.load(f)
        assert "version" in data
        assert "venvs" in data
        assert len(data["venvs"]) == 5


def test_lock_timeout(tmp_path):
    """Lock timeout raises CacheError with clear message."""
    cache_file = tmp_path / "cache.json"
    cache = Cache(cache_file)

    # Acquire lock manually to simulate held lock
    with cache._lock:
        # Try to write from another cache instance (will timeout)
        cache2 = Cache(cache_file)
        with pytest.raises(CacheError) as exc_info:
            project_path = tmp_path / "test"
            project_path.mkdir()
            cache2.add_mapping(project_path, "${HOME}/test", "test", "12345678")

        assert "lock" in str(exc_info.value).lower()
        assert "10 seconds" in str(exc_info.value)


# ============================================================================
# Edge Cases
# ============================================================================


def test_corrupted_cache_file(tmp_path):
    """Invalid JSON is handled gracefully."""
    cache_file = tmp_path / "cache.json"

    # Write invalid JSON
    cache_file.write_text("{ invalid json }")

    # Cache should handle corrupted file gracefully
    cache = Cache(cache_file)
    mappings = cache.list_all()
    assert mappings == {}


def test_missing_fields_in_mapping(tmp_path):
    """Missing fields in mappings don't crash."""
    cache_file = tmp_path / "cache.json"

    # Manually create cache with missing fields
    data = {
        "version": "1.0",
        "venvs": {
            "/some/path": {
                "venv_path": "${HOME}/venvs/test",
                # Missing other fields
            }
        },
    }
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w") as f:
        json.dump(data, f)

    # Cache should handle missing fields gracefully
    cache = Cache(cache_file)
    mappings = cache.list_all()
    assert len(mappings) == 1


def test_update_existing_mapping(tmp_path):
    """Updating existing mapping preserves created_at."""
    cache_file = tmp_path / "cache.json"
    cache = Cache(cache_file)

    project_path = tmp_path / "test-project"
    project_path.mkdir()

    venv_path = generate_venv_path(project_path)
    project_name = get_project_name(project_path)
    path_hash = generate_hash(project_path)

    # Add initial mapping
    cache.add_mapping(project_path, venv_path, project_name, path_hash)
    mapping1 = cache.get_mapping(project_path)
    created_at = mapping1["created_at"]

    # Wait a moment
    time.sleep(0.01)

    # Update mapping
    cache.add_mapping(project_path, venv_path, project_name, path_hash)
    mapping2 = cache.get_mapping(project_path)

    # created_at should be preserved
    assert mapping2["created_at"] == created_at
    # last_validated should be updated
    assert mapping2["last_validated"] > created_at


def test_long_project_paths(tmp_path):
    """Very long project paths work correctly."""
    cache_file = tmp_path / "cache.json"
    cache = Cache(cache_file)

    # Create a deeply nested path
    long_path = tmp_path
    for i in range(20):
        long_path = long_path / f"very-long-directory-name-{i}"
    long_path.mkdir(parents=True)

    venv_path = generate_venv_path(long_path)
    project_name = get_project_name(long_path)
    path_hash = generate_hash(long_path)

    cache.add_mapping(long_path, venv_path, project_name, path_hash)
    mapping = cache.get_mapping(long_path)

    assert mapping is not None
    assert mapping["venv_path"] == venv_path


def test_special_chars_in_paths(tmp_path):
    """Paths with spaces, unicode work correctly."""
    cache_file = tmp_path / "cache.json"
    cache = Cache(cache_file)

    # Create path with spaces and unicode
    project_path = tmp_path / "my project with spaces"
    project_path.mkdir()

    venv_path = generate_venv_path(project_path)
    project_name = get_project_name(project_path)
    path_hash = generate_hash(project_path)

    cache.add_mapping(project_path, venv_path, project_name, path_hash)
    mapping = cache.get_mapping(project_path)

    assert mapping is not None
    assert mapping["venv_path"] == venv_path


# ============================================================================
# Migration Tests
# ============================================================================


def test_migrate_if_needed_no_op(tmp_path):
    """Migration is no-op for current version."""
    cache_file = tmp_path / "cache.json"
    cache = Cache(cache_file)

    # Add a mapping to create cache
    project_path = tmp_path / "test"
    project_path.mkdir()
    venv_path = generate_venv_path(project_path)
    project_name = get_project_name(project_path)
    path_hash = generate_hash(project_path)

    cache.add_mapping(project_path, venv_path, project_name, path_hash)

    # Read version before migration
    with open(cache_file) as f:
        data_before = json.load(f)

    # Call migrate
    cache.migrate_if_needed()

    # Read version after migration
    with open(cache_file) as f:
        data_after = json.load(f)

    # Should be unchanged
    assert data_before["version"] == data_after["version"]
    assert data_before["venvs"] == data_after["venvs"]


def test_migrate_if_needed_adds_version(tmp_path):
    """Missing version field is added during migration."""
    cache_file = tmp_path / "cache.json"

    # Create cache without version field
    data = {"venvs": {}}
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w") as f:
        json.dump(data, f)

    # Load cache (should migrate)
    cache = Cache(cache_file)
    cache.migrate_if_needed()

    # Verify version was added
    with open(cache_file) as f:
        data_after = json.load(f)

    assert "version" in data_after
    assert data_after["version"] == Cache.CURRENT_VERSION


def test_symlink_resolution(tmp_path):
    """Project paths with symlinks are resolved correctly."""
    cache_file = tmp_path / "cache.json"
    cache = Cache(cache_file)

    # Create real directory
    real_path = tmp_path / "real-project"
    real_path.mkdir()

    # Create symlink to it
    link_path = tmp_path / "link-project"
    try:
        link_path.symlink_to(real_path)
    except OSError:
        # Symlinks might not be supported (Windows without admin)
        pytest.skip("Symlinks not supported on this system")

    venv_path = generate_venv_path(real_path)
    project_name = get_project_name(real_path)
    path_hash = generate_hash(real_path)

    # Add mapping via symlink
    cache.add_mapping(link_path, venv_path, project_name, path_hash)

    # Get mapping via real path
    mapping = cache.get_mapping(real_path)
    assert mapping is not None

    # Get mapping via symlink
    mapping2 = cache.get_mapping(link_path)
    assert mapping2 is not None

    # Should be the same mapping
    assert mapping == mapping2


def test_validation_result_properties():
    """ValidationResult properties work correctly."""
    result_valid = ValidationResult(status="valid", issues=[])
    assert result_valid.is_valid
    assert not result_valid.is_orphaned
    assert not result_valid.has_mismatch

    result_orphaned = ValidationResult(status="orphaned", issues=["Project missing"])
    assert not result_orphaned.is_valid
    assert result_orphaned.is_orphaned
    assert not result_orphaned.has_mismatch

    result_mismatch = ValidationResult(status="mismatch", issues=["Path mismatch"])
    assert not result_mismatch.is_valid
    assert not result_mismatch.is_orphaned
    assert result_mismatch.has_mismatch


def test_cache_error_exception():
    """CacheError can be raised and caught."""
    try:
        raise CacheError("Test error message")
    except CacheError as e:
        assert str(e) == "Test error message"
    except Exception:
        pytest.fail("CacheError should be caught as CacheError")


def test_default_cache_path():
    """Default cache path is in user home directory."""
    cache = Cache()
    assert cache._cache_path.is_absolute()
    assert ".prime-uve" in str(cache._cache_path)
    assert "cache.json" in str(cache._cache_path)


def test_empty_cache_file(tmp_path):
    """Empty cache file is handled gracefully."""
    cache_file = tmp_path / "cache.json"
    cache_file.write_text("")

    cache = Cache(cache_file)
    mappings = cache.list_all()
    assert mappings == {}


def test_cache_not_a_dict(tmp_path):
    """Cache file containing non-dict JSON is handled."""
    cache_file = tmp_path / "cache.json"
    cache_file.write_text('["not", "a", "dict"]')

    cache = Cache(cache_file)
    mappings = cache.list_all()
    assert mappings == {}
