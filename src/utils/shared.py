"""Shared utilities for docstring converters.

This module contains functions that are shared between markdown and TSX converters.
"""

import importlib
import inspect
import logging
import os
import pkgutil
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, TypeVar

from tqdm import tqdm

logger = logging.getLogger(__name__)

T = TypeVar("T")


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


@dataclass
class ModuleFileConfig:
    """Configuration for module file processing."""

    file_path: str
    modules: list[tuple[ModuleType, str]]
    output_dir: Path
    output_extension: str
    converter_func: Callable[[ModuleType, str], str]
    exclude_private: bool = False


@dataclass
class PackageConfig:
    """Configuration for processing a package."""

    package_name: str
    output_dir: Path
    exclude_private: bool
    converter_func: Callable[[ModuleType, str], str]
    output_extension: str
    progress_desc: str


def _walk_package(package_path: str) -> list[str]:
    """Walk through a package directory and collect Python files.

    Args:
        package_path: Path to the package directory

    Returns:
        list[str]: List of absolute paths to Python files in the package directory
    """
    python_files: list[str] = []
    for root, _, files in os.walk(package_path):
        python_files.extend(str(Path(root) / file) for file in files if file.endswith(".py"))
    return python_files


def collect_package_modules(
    package: ModuleType,
    *,
    exclude_private: bool = False,
) -> list[tuple[ModuleType, str]]:
    """Collect all modules in a package recursively.

    Args:
        package: Python package
        exclude_private: Whether to exclude private modules

    Returns:
        list: List of (module, module_name) tuples
    """
    modules: list[tuple[ModuleType, str]] = []
    if hasattr(package, "__file__") and package.__file__:
        modules.append((package, package.__name__))
    for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__, f"{package.__name__}."):
        if exclude_private and any(part.startswith("_") for part in module_name.split(".")):
            continue
        try:
            module = importlib.import_module(module_name)
        except (ImportError, AttributeError):
            continue
        if hasattr(module, "__file__") and module.__file__:
            modules.append((module, module_name))
        if is_pkg:
            modules.extend(collect_package_modules(module, exclude_private=exclude_private))
    return modules


def group_modules_by_file(modules: list[tuple[ModuleType, str]]) -> dict[str, list[tuple[ModuleType, str]]]:
    """Group modules by their source file.

    Args:
        modules: List of (module, module_name) tuples

    Returns:
        dict[str, list[tuple[ModuleType, str]]]: Dictionary mapping file paths to lists of
            (module, module_name) tuples that share the same source file
    """
    grouped: dict[str, list[tuple[ModuleType, str]]] = {}
    for module, module_name in modules:
        try:
            file_path = inspect.getfile(module)
            if file_path not in grouped:
                grouped[file_path] = []
            grouped[file_path].append((module, module_name))
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


def collect_module_members(module: ModuleType) -> tuple[list[tuple[str, type]], list[tuple[str, Callable[..., Any]]]]:
    """Collect classes and functions from a module.

    Args:
        module: Module to collect members from

    Returns:
        tuple[list[tuple[str, type]], list[tuple[str, Callable[..., Any]]]]: A tuple containing:
            - List of (name, class) tuples for classes defined in the module
            - List of (name, function) tuples for functions defined in the module
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


def build_output_dir(config: ModuleFileConfig, module_name: str, file_name: str) -> Path:
    """Build output directory path for a module.

    Args:
        config: Module file configuration
        module_name: Name of the module
        file_name: Name of the file

    Returns:
        Path: Output directory path constructed from the module name and file name,
            with special handling for __init__.py files
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
    return config.output_dir.joinpath(*path_segments)


def process_module_file(
    file_path: str,
    modules: list[tuple[ModuleType, str]],
    converter_func: Callable[[ModuleType, str], str],
    output_dir: Path,
    exclude_private: bool = False,
) -> bool:
    """Process a module file and generate documentation.

    Args:
        file_path: Path to the module file
        modules: List of (module, module_name) tuples
        converter_func: Function to convert module to documentation
        output_dir: Directory to write output files
        exclude_private: Whether to exclude private members

    Returns:
        bool: True if processing was successful, False otherwise
    """
    try:
        path_obj = Path(file_path)
        file_name = path_obj.stem
        if file_name == "__init__":
            return False

        module, module_name = min(modules, key=lambda x: len(x[1]))
        output_dir = build_output_dir(
            ModuleFileConfig(
                file_path=file_path,
                modules=modules,
                output_dir=output_dir,
                output_extension=".tsx",
                converter_func=converter_func,
                exclude_private=exclude_private,
            ),
            module_name,
            file_name,
        )

        content = converter_func(module, module_name)
        output_file = output_dir / "page.tsx"
        output_file.write_text(content)

        return True
    except (ImportError, AttributeError, OSError, ValueError):
        logger.exception(f"Failed to process module file {file_path}")
        return False


def package_to_structure(config: PackageConfig) -> None:
    """Process a package and generate documentation structure.

    Args:
        config: Configuration for package processing
    """
    try:
        # Import the package
        package = importlib.import_module(config.package_name)
        if not hasattr(package, "__file__"):
            logger.error("Package %s has no __file__ attribute", config.package_name)
            return

        # Collect all modules in the package
        modules = collect_package_modules(
            package,
            exclude_private=config.exclude_private,
        )

        # Group modules by file
        module_groups = group_modules_by_file(modules)

        # Process each file with progress bar
        with tqdm(total=len(module_groups), desc=config.progress_desc) as pbar:
            for file_path, file_modules in module_groups.items():
                if process_module_file(
                    file_path,
                    file_modules,
                    config.converter_func,
                    output_dir=config.output_dir,
                    exclude_private=config.exclude_private,
                ):
                    pbar.update(1)
                else:
                    pbar.update(1)

    except Exception:
        logger.exception("Error processing package %s", config.package_name)
