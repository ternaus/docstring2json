"""Shared utilities for docstring converters.

This module contains functions that are shared between markdown and TSX converters.
"""

import importlib
import inspect
import logging
import pkgutil
import re
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import TypeVar

from tqdm import tqdm

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Error messages
ERR_NO_FILE_ATTR = "Package has no __file__ attribute"


def normalize_anchor_id(text: str) -> str:
    """Normalize text for use as an anchor ID.

    Args:
        text: Text to normalize

    Returns:
        str: Normalized text suitable for use as an anchor ID, with special characters removed
            and spaces replaced with hyphens
    """
    # Remove special characters and replace spaces with hyphens
    return re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower().replace(" ", "-")


def get_package_structure(package_name: str) -> dict[str, Path]:
    """Get the file structure of an installed package.

    Args:
        package_name: Name of the package

    Returns:
        dict[str, Path]: Dictionary mapping module names to their relative paths
    """
    # Import the package
    package = importlib.import_module(package_name)
    if not hasattr(package, "__file__"):
        raise ImportError(ERR_NO_FILE_ATTR) from None

    # Get the package directory
    package_file = getattr(package, "__file__", "")
    if not package_file:
        raise ImportError(ERR_NO_FILE_ATTR) from None

    package_dir = Path(package_file).parent
    if not package_dir.is_dir():
        package_dir = package_dir.parent

    # Store module paths
    module_paths: dict[str, Path] = {}

    def process_module(module: ModuleType, module_name: str) -> None:
        """Process a module and its submodules."""
        try:
            # Get the module's file
            file_path = Path(inspect.getfile(module))
            # Get relative path from package directory
            relative_path = file_path.relative_to(package_dir)
            module_paths[module_name] = relative_path

            # Process submodules
            if hasattr(module, "__path__"):
                for _, submodule_name, _is_pkg in pkgutil.iter_modules(module.__path__, f"{module_name}."):
                    try:
                        submodule = importlib.import_module(submodule_name)
                        process_module(submodule, submodule_name)
                    except (ImportError, AttributeError):
                        continue
        except (TypeError, ValueError):
            # Skip modules without source files
            pass

    # Process the package and all its submodules
    process_module(package, package_name)
    return module_paths


def process_module(
    module_name: str,
    module_path: Path,
    output_dir: Path,
    converter_func: Callable[[ModuleType, str], str],
    exclude_private: bool = False,
) -> None:
    """Process a single module and generate its documentation.

    Args:
        module_name: Full module name (e.g. "albumentations.augmentations.transforms")
        module_path: Relative path to the module
        output_dir: Directory to write output files
        converter_func: Function to convert module to TSX
        exclude_private: Whether to exclude private members
    """
    try:
        # Skip private modules if requested
        if exclude_private and any(part.startswith("_") for part in module_name.split(".")):
            return

        # Import the module
        module = importlib.import_module(module_name)

        # Skip __init__.py files
        if module_path.name == "__init__.py":
            return

        # Build output path
        output_path = output_dir / module_path.parent / module_path.stem

        # Create output directory
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate content
        content = converter_func(module, module_name)

        # Write output file
        output_file = output_path / "page.tsx"
        output_file.write_text(content)

    except Exception:
        logger.exception("Failed to process module %s", module_name)


def process_package(
    package_name: str,
    output_dir: Path,
    converter_func: Callable[[ModuleType, str], str],
    exclude_private: bool = False,
) -> None:
    """Process an installed package and generate documentation.

    Args:
        package_name: Name of the package
        output_dir: Directory to write output files
        converter_func: Function to convert module to TSX
        exclude_private: Whether to exclude private members
    """
    # Get the package structure
    module_paths = get_package_structure(package_name)

    # Process each module with progress bar
    with tqdm(total=len(module_paths), desc=f"Processing {package_name}") as pbar:
        for module_name, module_path in module_paths.items():
            process_module(
                module_name=module_name,
                module_path=module_path,
                output_dir=output_dir,
                converter_func=converter_func,
                exclude_private=exclude_private,
            )
            pbar.update(1)
