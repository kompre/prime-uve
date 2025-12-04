"""Cache system for tracking project → venv mappings.

This module provides a persistent, thread-safe cache for managing virtual environment
mappings. It supports validation, migration, and concurrent access through file locking.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from filelock import FileLock, Timeout

from .paths import expand_path_variables

logger = logging.getLogger(__name__)


class CacheError(Exception):
    """Raised when cache operations fail."""

    pass


@dataclass
class ValidationResult:
    """Result of validating a cached mapping."""

    status: Literal["valid", "orphaned", "mismatch", "error"]
    issues: list[str]  # Human-readable issue descriptions

    @property
    def is_valid(self) -> bool:
        """True if status is 'valid'."""
        return self.status == "valid"

    @property
    def is_orphaned(self) -> bool:
        """True if project or venv is missing."""
        return self.status == "orphaned"

    @property
    def has_mismatch(self) -> bool:
        """True if .env.uve path doesn't match cache."""
        return self.status == "mismatch"


class Cache:
    """Thread-safe cache for project → venv mappings."""

    CURRENT_VERSION = "1.0"

    def __init__(self, cache_path: Path | None = None):
        """Initialize cache.

        Args:
            cache_path: Path to cache file. Defaults to ~/.prime-uve/cache.json
        """
        self._cache_path = cache_path or self._default_cache_path()
        self._lock_path = self._cache_path.with_suffix(".lock")
        self._lock = FileLock(self._lock_path, timeout=10)

    @staticmethod
    def _default_cache_path() -> Path:
        """Get default cache path (~/.prime-uve/cache.json)."""
        home = Path.home()
        return home / ".prime-uve" / "cache.json"

    def _load(self) -> dict:
        """Load cache with lock held.

        Returns:
            Cache data dict with 'version' and 'venvs' keys
        """
        try:
            with self._lock:
                if not self._cache_path.exists():
                    return {"version": self.CURRENT_VERSION, "venvs": {}}

                try:
                    with open(self._cache_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    # Handle corrupted or invalid cache
                    if not isinstance(data, dict):
                        logger.warning(
                            "Cache file corrupted (not a dict), starting fresh"
                        )
                        return {"version": self.CURRENT_VERSION, "venvs": {}}

                    # Ensure required fields exist
                    if "venvs" not in data:
                        data["venvs"] = {}

                    return data
                except json.JSONDecodeError:
                    logger.warning(
                        "Cache file corrupted (invalid JSON), starting fresh"
                    )
                    return {"version": self.CURRENT_VERSION, "venvs": {}}
                except Exception as e:
                    logger.error(f"Error loading cache: {e}")
                    return {"version": self.CURRENT_VERSION, "venvs": {}}
        except Timeout:
            raise CacheError(
                "Could not acquire cache lock after 10 seconds. "
                "Another process may be using the cache. Please try again."
            )

    def _save(self, data: dict) -> None:
        """Save cache with lock held.

        Args:
            data: Cache data dict to save

        Raises:
            CacheError: If cache cannot be written
        """
        try:
            with self._lock:
                # Create parent directory if needed
                self._cache_path.parent.mkdir(parents=True, exist_ok=True)

                # Write to temp file then rename for atomicity
                temp_path = self._cache_path.with_suffix(".tmp")
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)

                # Atomic rename
                temp_path.replace(self._cache_path)
        except Timeout:
            raise CacheError(
                "Could not acquire cache lock after 10 seconds. "
                "Another process may be using the cache. Please try again."
            )
        except OSError as e:
            raise CacheError(f"Failed to write cache file: {e}")

    def _migrate_data(self, data: dict) -> None:
        """Migrate cache data to current version if needed.

        Args:
            data: Cache data dict (modified in-place)
        """
        # Add version field if missing
        if "version" not in data:
            data["version"] = self.CURRENT_VERSION
            logger.info("Added version field to cache")

        # Future migrations would go here
        # if data["version"] == "1.0" and self.CURRENT_VERSION == "2.0":
        #     # Perform migration logic
        #     data["version"] = "2.0"

    def add_mapping(
        self,
        project_path: Path,
        venv_path: str,
        project_name: str,
        path_hash: str,
    ) -> None:
        """Add or update a project → venv mapping.

        Args:
            project_path: Absolute path to project directory
            venv_path: Venv path with ${HOME} variable (not expanded)
            project_name: Sanitized project name
            path_hash: 8-character hash

        Raises:
            CacheError: If cache cannot be written
        """
        # Resolve project path to handle symlinks
        project_path = project_path.resolve()
        project_key = str(project_path)

        # Expand venv path for storage
        venv_path_expanded = str(expand_path_variables(venv_path))

        # Load current cache
        data = self._load()

        # Get existing mapping to preserve created_at
        existing = data["venvs"].get(project_key, {})
        created_at = existing.get("created_at")
        if not created_at:
            created_at = datetime.now(timezone.utc).isoformat()

        # Create new mapping
        data["venvs"][project_key] = {
            "venv_path": venv_path,
            "venv_path_expanded": venv_path_expanded,
            "project_name": project_name,
            "path_hash": path_hash,
            "created_at": created_at,
            "last_validated": datetime.now(timezone.utc).isoformat(),
        }

        # Save updated cache
        self._save(data)

    def get_mapping(self, project_path: Path) -> dict | None:
        """Get mapping for a project.

        Args:
            project_path: Absolute path to project directory

        Returns:
            Mapping dict or None if not found
        """
        project_path = project_path.resolve()
        project_key = str(project_path)

        data = self._load()
        return data["venvs"].get(project_key)

    def remove_mapping(self, project_path: Path) -> bool:
        """Remove a project → venv mapping.

        Args:
            project_path: Absolute path to project directory

        Returns:
            True if removed, False if not found

        Raises:
            CacheError: If cache cannot be written
        """
        project_path = project_path.resolve()
        project_key = str(project_path)

        data = self._load()

        if project_key not in data["venvs"]:
            return False

        del data["venvs"][project_key]
        self._save(data)
        return True

    def list_all(self) -> dict[str, dict]:
        """Get all cached mappings.

        Returns:
            Dict of project_path → mapping
        """
        data = self._load()
        return data["venvs"]

    def clear(self) -> None:
        """Remove all mappings from cache.

        Raises:
            CacheError: If cache cannot be written
        """
        data = {"version": self.CURRENT_VERSION, "venvs": {}}
        self._save(data)

    def validate_mapping(self, project_path: Path) -> ValidationResult:
        """Validate a mapping against filesystem reality.

        Checks:
        - Project directory exists
        - Venv directory exists (using expanded path)
        - .env.uve exists and contains matching venv path

        Args:
            project_path: Absolute path to project directory

        Returns:
            ValidationResult with status and issues
        """
        project_path = project_path.resolve()
        project_key = str(project_path)

        # Get mapping from cache
        data = self._load()
        mapping = data["venvs"].get(project_key)

        if not mapping:
            return ValidationResult(
                status="error", issues=["Mapping not found in cache"]
            )

        issues = []

        try:
            # Check 1: Project directory exists
            if not project_path.exists():
                issues.append("Project directory does not exist")

            # Check 2: Venv directory exists
            venv_path_expanded = Path(mapping["venv_path_expanded"])
            if not venv_path_expanded.exists():
                issues.append("Venv directory does not exist")

            # Check 3: .env.uve exists
            env_file = project_path / ".env.uve"
            if not env_file.exists():
                issues.append(".env.uve file does not exist")
            else:
                # Check 4: .env.uve path matches cache
                try:
                    env_content = env_file.read_text(encoding="utf-8").strip()
                    # Parse UV_PROJECT_ENVIRONMENT="..." from .env.uve
                    expected_prefix = 'UV_PROJECT_ENVIRONMENT="'
                    if env_content.startswith(expected_prefix) and env_content.endswith(
                        '"'
                    ):
                        env_venv_path = env_content[len(expected_prefix) : -1]
                        cached_venv_path = mapping["venv_path"]
                        if env_venv_path != cached_venv_path:
                            issues.append(
                                f".env.uve path mismatch: "
                                f"cache has '{cached_venv_path}', "
                                f"file has '{env_venv_path}'"
                            )
                    else:
                        issues.append(".env.uve file format invalid")
                except Exception as e:
                    issues.append(f"Error reading .env.uve: {e}")

            # Determine status
            if not issues:
                status = "valid"
            elif any("mismatch" in issue for issue in issues):
                status = "mismatch"
            elif any("does not exist" in issue for issue in issues):
                status = "orphaned"
            else:
                status = "error"

            # Update last_validated timestamp
            if project_key in data["venvs"]:
                data["venvs"][project_key]["last_validated"] = datetime.now(
                    timezone.utc
                ).isoformat()
                self._save(data)

            return ValidationResult(status=status, issues=issues)

        except Exception as e:
            logger.error(f"Error validating mapping for {project_path}: {e}")
            return ValidationResult(status="error", issues=[f"Validation error: {e}"])

    def validate_all(self) -> dict[str, ValidationResult]:
        """Validate all cached mappings.

        Returns:
            Dict of project_path → ValidationResult
        """
        results = {}
        for project_path_str in self.list_all().keys():
            project_path = Path(project_path_str)
            results[project_path_str] = self.validate_mapping(project_path)
        return results

    def migrate_if_needed(self) -> None:
        """Migrate cache to current version if needed.

        Called automatically on load. Future-proofing for schema changes.
        """
        data = self._load()
        needs_migration = (
            "version" not in data or data["version"] != self.CURRENT_VERSION
        )
        if needs_migration:
            self._migrate_data(data)
            self._save(data)
