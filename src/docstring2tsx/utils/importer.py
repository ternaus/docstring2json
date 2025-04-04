"""Module for importing Python files."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


class ModuleImportError(Exception):
    """Error raised when a module cannot be imported."""

    def __init__(self, file_path: str | Path) -> None:
        """Initialize the error.

        Args:
            file_path: Path to the file that could not be imported
        """
        self.file_path = file_path
        super().__init__(f"Could not import module from {file_path}")


def import_module_from_file(file_path: str | Path) -> ModuleType:
    """Import a module from a file path.

    Args:
        file_path: Path to the Python file

    Returns:
        ModuleType: Imported module
    """
    # Convert to Path and resolve
    path = Path(file_path).resolve()

    # Get module name from file path
    module_name = path.stem

    # Create spec
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if not spec or not spec.loader:
        raise ModuleImportError(path)

    # Create module
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    # Execute module
    spec.loader.exec_module(module)

    return module
