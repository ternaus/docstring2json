"""Shared utilities for docstring converters.

This module contains functions that are shared between markdown and TSX converters.
"""

import importlib
import inspect
import logging
import pkgutil
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import FunctionType, ModuleType
from typing import Any, TypeVar

from tqdm import tqdm

logger = logging.getLogger(__name__)

T = TypeVar("T")


def normalize_anchor_id(module_name: str, name: str) -> str:
    """Normalize a name for use as an HTML anchor ID.

    Args:
        module_name: Module name
        name: Name to normalize

    Returns:
        Normalized name suitable for use as an HTML anchor ID
    """
    return f"{module_name.replace('.', '-')}-{name}".lower()


@dataclass
class ModuleFileConfig:
    """Configuration for module file processing."""

    file_path: str
    modules: Sequence[tuple[ModuleType, str]]
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


def _walk_package(package: ModuleType, package_name: str, exclude_private: bool) -> list[tuple[ModuleType, str]]:
    """Recursively walk through a package to find all modules.

    Args:
        package: Python package to walk through
        package_name: Name of the package
        exclude_private: Whether to exclude private modules

    Returns:
        List of (module, module_name) tuples
    """
    found: list[tuple[ModuleType, str]] = []
    if not hasattr(package, "__path__"):
        return found
    for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__, f"{package_name}."):
        if exclude_private and any(part.startswith("_") for part in module_name.split(".")):
            continue
        try:
            module = importlib.import_module(module_name)
        except (ImportError, AttributeError):
            continue
        if hasattr(module, "__file__") and module.__file__:
            found.append((module, module_name))
        if is_pkg:
            found.extend(_walk_package(module, module_name, exclude_private))
    return found


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
    modules.extend(_walk_package(package, package.__name__, exclude_private))
    return modules


def group_modules_by_file(
    modules: Sequence[tuple[ModuleType, str]],
) -> dict[str, list[tuple[ModuleType, str]]]:
    """Group modules by their file path.

    Args:
        modules: List of (module, module_name) tuples

    Returns:
        Dictionary mapping file paths to lists of (module, module_name) tuples
    """
    file_to_modules: dict[str, list[tuple[ModuleType, str]]] = defaultdict(list)

    for module, module_name in modules:
        if hasattr(module, "__file__") and module.__file__:
            file_to_modules[module.__file__].append((module, module_name))

    return file_to_modules


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


def collect_module_members(module: ModuleType) -> tuple[list[tuple[str, type[Any]]], list[tuple[str, FunctionType]]]:
    """Collect classes and functions from a module.

    Args:
        module: Python module

    Returns:
        Tuple of (classes, functions) where each is a list of (name, object) pairs
    """
    classes: list[tuple[str, type[Any]]] = []
    functions: list[tuple[str, FunctionType]] = []

    for name, obj in inspect.getmembers(module):
        # Skip private members
        if name.startswith("_"):
            continue

        # Only consider items defined in this module
        if hasattr(obj, "__module__") and obj.__module__ == module.__name__:
            if inspect.isclass(obj):
                classes.append((name, obj))
            elif inspect.isfunction(obj):
                functions.append((name, obj))

    return classes, functions


def build_output_dir(config: ModuleFileConfig, module_name: str, file_name: str) -> Path:
    """Build the output directory path for a module file.

    Args:
        config: Configuration for module file processing
        module_name: Full module name (e.g., 'package.module.submodule')
        file_name: Name of the file without extension

    Returns:
        Path to the output directory
    """
    parts = module_name.split(".")
    if len(parts) > 1:
        simplified_path = parts[1:]
        if simplified_path and simplified_path[-1] == file_name:
            simplified_path = simplified_path[:-1]
        simplified_path = [part for part in simplified_path if part != "__init__"]
        return config.output_dir / "/".join(simplified_path) / file_name
    return config.output_dir / file_name


def process_module_file(
    file_path: str,
    modules: Sequence[tuple[ModuleType, str]],
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
        output_dir.mkdir(parents=True, exist_ok=True)

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
