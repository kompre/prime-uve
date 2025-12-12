"""prime-uve: Virtual environment management for uv with external venv locations."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("prime-uve")
except PackageNotFoundError:
    __version__ = "unknown"


def main() -> None:
    print("Hello from prime-uve!")
