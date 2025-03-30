"""Shared utilities for docstring converters.

This module contains functions that are shared between markdown and TSX converters.
"""

import importlib
import inspect
import pkgutil
from collections import defaultdict
from collections.abc import Callable
from types import FunctionType, ModuleType
from typing import Any, TypeVar

T = TypeVar("T")


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


def normalize_anchor_id(module_name: str, item_name: str) -> str:
    """Normalize an anchor ID for linking.

    Args:
        module_name: Module name
        item_name: Item name

    Returns:
        Normalized anchor ID
    """
    return f"{module_name.replace('.', '-')}-{item_name}"


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
        modules: List of (name, module) pairs

    Returns:
        Dict mapping file paths to lists of (name, module) pairs
    """
    groups: dict[str, list[tuple[str, ModuleType]]] = defaultdict(list)

    for name, module in modules:
        try:
            file_path = inspect.getfile(module)
            groups[file_path].append((name, module))
        except (TypeError, OSError):
            pass

    return dict(groups)


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


def process_module_file(
    _file_path: str,
    modules: list[tuple[str, ModuleType]],
    *,
    github_repo: str | None = None,
    branch: str = "main",
    converter_func: Callable[[ModuleType, str | None, str], str],
) -> str:
    """Process a file containing multiple modules.

    Args:
        _file_path: Path to the file (unused)
        modules: List of (name, module) pairs
        github_repo: Base URL of the GitHub repository
        branch: Branch name for GitHub links
        converter_func: Function to convert modules to documentation

    Returns:
        Generated documentation content
    """
    content = []

    for _, module in modules:
        try:
            doc = converter_func(module, github_repo, branch)
            content.append(doc)
        except (ValueError, TypeError, AttributeError):
            pass

    return "\n\n".join(content)
