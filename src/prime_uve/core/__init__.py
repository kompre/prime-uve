"""Core utilities for prime-uve."""

from .cache import (
    Cache,
    CacheError,
    ValidationResult,
)
from .env_file import (
    EnvFileError,
    find_env_file,
    get_venv_path,
    read_env_file,
    update_env_file,
    write_env_file,
)
from .paths import (
    generate_hash,
    generate_venv_path,
    expand_path_variables,
    get_project_name,
    ensure_home_set,
)
from .project import (
    find_project_root,
    get_project_metadata,
    is_python_project,
    ProjectMetadata,
    ProjectError,
)

__all__ = [
    # cache module
    "Cache",
    "CacheError",
    "ValidationResult",
    # env_file module
    "EnvFileError",
    "find_env_file",
    "get_venv_path",
    "read_env_file",
    "update_env_file",
    "write_env_file",
    # paths module
    "generate_hash",
    "generate_venv_path",
    "expand_path_variables",
    "get_project_name",
    "ensure_home_set",
    # project module
    "find_project_root",
    "get_project_metadata",
    "is_python_project",
    "ProjectMetadata",
    "ProjectError",
]
