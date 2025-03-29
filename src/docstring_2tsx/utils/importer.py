"""Utilities for importing Python modules from files."""

import importlib.util
from pathlib import Path
from types import ModuleType


class ModuleImportError(ImportError):
    """Raised when a module cannot be imported."""

    def __init__(self, path: Path) -> None:
        """Initialize the error with a file path.

        Args:
            path: Path to the file that could not be imported
        """
        super().__init__()
        self.path = path

    def __str__(self) -> str:
        """Return a string representation of the error.

        Returns:
            Error message with the file path
        """
        return f"Could not import {self.path}"


def import_module_from_file(file_path: Path) -> ModuleType:
    """Import a module from a file path.

    Args:
        file_path: Path to the Python file

    Returns:
        The imported module

    Raises:
        ModuleImportError: If the module cannot be imported
    """
    try:
        return importlib.import_module(file_path.name)
    except ImportError as e:
        raise ModuleImportError(file_path) from e
