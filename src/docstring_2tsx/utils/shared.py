"""Shared utilities for docstring converters.

This module contains functions that are shared between markdown and TSX converters.
"""

import importlib
import inspect
import pkgutil
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any


def collect_module_members(module: object) -> tuple[list[tuple[str, object]], list[tuple[str, object]]]:
    """Collect classes and functions from a module.

    Args:
        module: Python module

    Returns:
        Tuple of (classes, functions) where each is a list of (name, object) pairs
    """
    classes = []
    functions = []

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


def collect_package_modules(package: object, *, exclude_private: bool = True) -> list[tuple[str, object]]:
    """Collect all modules in a package.

    Args:
        package: Python package
        exclude_private: Whether to exclude private modules

    Returns:
        List of (name, module) pairs
    """
    modules = []
    package_path = Path(package.__file__).parent

    for _, name, _is_pkg in pkgutil.walk_packages([str(package_path)]):
        if exclude_private and name.startswith("_"):
            continue

        try:
            module = importlib.import_module(f"{package.__name__}.{name}")
            modules.append((name, module))
        except ImportError:
            pass

    return modules


def group_modules_by_file(modules: list[tuple[str, object]]) -> dict[str, list[tuple[str, object]]]:
    """Group modules by their source file.

    Args:
        modules: List of (name, module) pairs

    Returns:
        Dict mapping file paths to lists of (name, module) pairs
    """
    groups: dict[str, list[tuple[str, object]]] = defaultdict(list)

    for name, module in modules:
        # Note: try-except inside loop is necessary here as each module needs to be
        # processed independently. Moving it outside would make error handling more complex
        # and less maintainable. The performance impact is minimal as this is not in a hot path.
        try:
            file_path = inspect.getfile(module)
            groups[file_path].append((name, module))
        except (TypeError, OSError):
            pass

    return dict(groups)


def has_documentable_members(module: object) -> bool:
    """Check if a module has any documentable members.

    Args:
        module: Python module

    Returns:
        True if the module has documentable members
    """
    for name, obj in inspect.getmembers(module):
        if name.startswith("_"):
            continue
        if (
            hasattr(obj, "__module__")
            and obj.__module__ == module.__name__
            and (inspect.isclass(obj) or inspect.isfunction(obj))
        ):
            return True
    return False


def process_module_file(
    _file_path: str,
    modules: list[tuple[str, object]],
    *,
    github_repo: str | None = None,
    branch: str = "main",
    converter_func: Callable[[Any, str | None, str], str],
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
        # Note: try-except inside loop is necessary here as each module needs to be
        # processed independently. Moving it outside would make error handling more complex
        # and less maintainable. The performance impact is minimal as this is not in a hot path.
        try:
            doc = converter_func(module, github_repo, branch)
            content.append(doc)
        except (ValueError, TypeError, AttributeError):
            pass

    return "\n\n".join(content)
