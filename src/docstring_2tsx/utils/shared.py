"""Shared utilities for docstring converters.

This module contains functions that are shared between markdown and TSX converters.
"""

import importlib
import inspect
import logging
import pkgutil
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def collect_module_members(module: ModuleType) -> tuple[list[tuple[str, type]], list[tuple[str, Callable[..., Any]]]]:
    """Collect classes and functions from a module.

    Args:
        module: Module to collect members from

    Returns:
        tuple[list[tuple[str, type]], list[tuple[str, Callable[..., Any]]]]: Tuple of (classes, functions)
    """
    classes: list[tuple[str, type]] = []
    functions: list[tuple[str, Callable[..., Any]]] = []

    for name, obj in inspect.getmembers(module):
        # Skip private members and imported objects
        if name.startswith("_") or inspect.getmodule(obj) != inspect.getmodule(module):
            continue

        if inspect.isclass(obj):
            classes.append((name, obj))
        elif inspect.isfunction(obj):
            functions.append((name, obj))

    return classes, functions


def normalize_anchor_id(text: str) -> str:
    """Normalize text for use as an anchor ID.

    Args:
        text: Text to normalize

    Returns:
        str: Normalized text suitable for use as an anchor ID
    """
    # Remove special characters and replace spaces with hyphens
    return text.strip().lower().replace(" ", "-")


def collect_package_modules(
    package: ModuleType,
    package_name: str = "",
    *,
    exclude_private: bool = False,
) -> list[tuple[ModuleType, str]]:
    """Collect all modules in a package recursively.

    Args:
        package: Python package
        package_name: Name of the package
        exclude_private: Whether to exclude private modules

    Returns:
        list: List of (module, module_name) tuples
    """
    modules_to_process: list[tuple[ModuleType, str]] = []

    # Process the root module
    if hasattr(package, "__file__") and package.__file__:
        modules_to_process.append((package, package.__name__))

    # Find all submodules recursively using a queue
    modules_to_explore = [(package, package_name)]
    explored_modules = set()

    while modules_to_explore:
        current_package, current_name = modules_to_explore.pop(0)
        if current_name in explored_modules:
            continue

        explored_modules.add(current_name)

        if not hasattr(current_package, "__path__"):
            continue

        for _module_finder, module_name, is_pkg in pkgutil.iter_modules(current_package.__path__, f"{current_name}."):
            if exclude_private and any(part.startswith("_") for part in module_name.split(".")):
                continue

            try:
                module = importlib.import_module(module_name)
                if hasattr(module, "__file__") and module.__file__:
                    modules_to_process.append((module, module_name))

                    # If this is a package, add it to the exploration queue
                    if is_pkg:
                        modules_to_explore.append((module, module_name))
            except (ImportError, AttributeError):
                pass

    return modules_to_process


def group_modules_by_file(modules: list[tuple[str, ModuleType]]) -> dict[str, list[tuple[str, ModuleType]]]:
    """Group modules by their source file.

    Args:
        modules: List of (name, module) tuples

    Returns:
        dict[str, list[tuple[str, ModuleType]]]: Dictionary mapping file paths to module lists
    """
    grouped: dict[str, list[tuple[str, ModuleType]]] = {}
    for name, module in modules:
        try:
            file_path = inspect.getfile(module)
            if file_path not in grouped:
                grouped[file_path] = []
            grouped[file_path].append((name, module))
        except (TypeError, ValueError):
            # Skip modules without source files
            pass
    return grouped


def has_documentable_members(
    module: ModuleType,
    *,
    exclude_private: bool,
) -> bool:
    """Check if a module has documentable members.

    Args:
        module: Module to check
        exclude_private: Whether to exclude private members

    Returns:
        bool: True if the module has documentable members
    """
    # Skip __init__.py files
    if hasattr(module, "__file__") and module.__file__ and module.__file__.endswith("__init__.py"):
        return False

    for name, obj in inspect.getmembers(module):
        if exclude_private and name.startswith("_"):
            continue

        if (
            (inspect.isclass(obj) or inspect.isfunction(obj))
            and hasattr(obj, "__module__")
            and obj.__module__ == module.__name__
        ):
            return True

    return False


def build_output_dir(output_dir: Path, module_name: str, file_name: str) -> Path:
    """Build output directory path for a module.

    Args:
        output_dir: Base output directory
        module_name: Name of the module
        file_name: Name of the file

    Returns:
        Path: Output directory path
    """
    # Convert module name to path segments
    path_segments = module_name.split(".")

    # Handle special cases
    if file_name == "__init__":
        # For __init__.py files, use the parent directory name
        path_segments = path_segments[:-1]
    elif not file_name.startswith("__"):
        # For regular files, append the file name
        path_segments.append(file_name)

    # Build the output path
    return output_dir.joinpath(*path_segments)


def process_module_file(
    file_path: str,
    modules: list[tuple[ModuleType, str]],
    converter_func: Callable[[ModuleType, str], str],
    output_dir: Path,
) -> bool:
    """Process a module file and generate documentation.

    Args:
        file_path: Path to the module file
        modules: List of (module, module_name) tuples
        converter_func: Function to convert module to documentation
        output_dir: Directory to write output files

    Returns:
        bool: True if processing was successful, False otherwise
    """
    try:
        path_obj = Path(file_path)
        file_name = path_obj.stem
        if file_name == "__init__":
            return False

        module, module_name = min(modules, key=lambda x: len(x[1]))
        module_output_dir = build_output_dir(
            output_dir,
            module_name,
            file_name,
        )
        module_output_dir.mkdir(parents=True, exist_ok=True)

        content = converter_func(module, module_name)
        output_file = module_output_dir / "page.tsx"
        output_file.write_text(content)

        return True
    except (ImportError, AttributeError, OSError, ValueError):
        logger.exception(f"Failed to process module file {file_path}")
        return False
