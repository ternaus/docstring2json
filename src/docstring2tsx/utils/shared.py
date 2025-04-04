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

from tqdm import tqdm

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


def group_modules_by_file(modules: list[tuple[ModuleType, str]]) -> dict[Path, list[tuple[ModuleType, str]]]:
    """Group modules by their source file Path.

    Args:
        modules: List of (module, name) tuples

    Returns:
        dict[Path, list[tuple[ModuleType, str]]]: Dictionary mapping file Paths to module lists
    """
    grouped: dict[Path, list[tuple[ModuleType, str]]] = {}
    for module, name in modules:
        try:
            file_path_str = inspect.getfile(module)
            file_path = Path(file_path_str)
            if file_path not in grouped:
                grouped[file_path] = []
            grouped[file_path].append((module, name))
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


def get_path_segments(module_name: str, file_name: str) -> list[str]:
    """Determine the output path segments based on module and file name.

    Args:
        module_name: Full module name (e.g., "package.submodule")
        file_name: Base name of the file (e.g., "my_module" or "__init__")

    Returns:
        list[str]: List of path segments for the output directory.
    """
    segments = module_name.split(".")
    if file_name == "__init__":
        # For __init__.py files, use the parent directory name.
        return segments[:-1]
    if not file_name.startswith("__"):
        # For regular files, append the file name.
        segments.append(file_name)
    return segments


def build_output_dir(output_dir: Path, module_name: str, file_name: str) -> Path:
    """Build output directory path for a module.

    Args:
        output_dir: Base output directory
        module_name: Name of the module
        file_name: Name of the file

    Returns:
        Path: Output directory path
    """
    # Determine path segments using the helper function
    path_segments = get_path_segments(module_name, file_name)
    # Build the output path
    return output_dir.joinpath(*path_segments)


def write_module_output(
    module: ModuleType,
    module_name: str,
    output_dir: Path,
    file_name: str,
    converter_func: Callable[[ModuleType, str], str],
) -> None:
    """Generate and write the documentation output for a module.

    Args:
        module: The module object to document.
        module_name: The full name of the module.
        output_dir: The base directory to write output files.
        file_name: The base name of the source file (without extension).
        converter_func: The function to convert module data to string content.
    """
    module_output_dir = build_output_dir(output_dir, module_name, file_name)
    module_output_dir.mkdir(parents=True, exist_ok=True)
    content = converter_func(module, module_name)
    output_file = module_output_dir / "page.tsx"  # Assuming .tsx extension
    output_file.write_text(content)


def process_module_file(
    file_path: Path,
    modules: list[tuple[ModuleType, str]],
    converter_func: Callable[[ModuleType, str], str],
    output_dir: Path,
) -> bool:
    """Process a module file and generate documentation.

    Args:
        file_path: Path to the module file
        modules: List of (module, module_name) tuples associated with the file
        converter_func: Function to convert module to documentation
        output_dir: Base directory to write output files

    Returns:
        bool: True if processing was successful, False otherwise
    """
    try:
        file_name = file_path.stem
        if file_name == "__init__":
            return False  # Skip __init__.py files

        # Find the module with the shortest name (likely the primary module)
        module, module_name = min(modules, key=lambda x: len(x[1]))

        # Generate and write the output using the helper function
        write_module_output(module, module_name, output_dir, file_name, converter_func)
        return True
    except (ImportError, AttributeError, OSError, ValueError):
        logger.exception(f"Failed to process module file {file_path}")
        return False


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
    # Find all modules in the package
    try:
        package = importlib.import_module(package_name)
    except ImportError:
        logger.exception(f"Failed to import package {package_name}")
        return

    modules_with_names = collect_package_modules(package, package_name, exclude_private=exclude_private)

    # Group modules by file path
    modules_by_file = group_modules_by_file(modules_with_names)

    # Process each module file with progress bar
    with tqdm(total=len(modules_by_file), desc=f"Processing {package_name}") as pbar:
        for file_path, file_modules in modules_by_file.items():
            process_module_file(
                file_path=file_path,  # Pass Path object
                modules=file_modules,
                converter_func=converter_func,
                output_dir=output_dir,
            )
            pbar.update(1)
