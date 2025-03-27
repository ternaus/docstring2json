"""Shared utilities for docstring converters.

This module contains functions that are shared between markdown and TSX converters.
"""

import importlib
import inspect
import logging
import pkgutil
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tqdm import tqdm

logger = logging.getLogger(__name__)


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
class GitHubConfig:
    """Configuration for GitHub repository links."""

    github_repo: str | None
    branch: str


@dataclass
class ModuleFileConfig:
    """Configuration for processing a module file."""

    file_path: str
    modules: list[tuple[object, str]]
    output_dir: Path
    exclude_private: bool
    github_config: GitHubConfig | None
    converter_func: Callable[[Any, str | None, str], str]
    output_extension: str


@dataclass
class PackageConfig:
    """Configuration for processing a package."""

    package_name: str
    output_dir: Path
    exclude_private: bool
    github_repo: str | None
    branch: str
    converter_func: Callable[[Any, str | None, str], str]
    output_extension: str
    progress_desc: str


def collect_package_modules(
    package: object,
    package_name: str,
    *,
    exclude_private: bool,
) -> list[tuple[object, str]]:
    """Collect all modules in a package.

    Args:
        package (object): The package object
        package_name (str): Name of the package
        exclude_private (bool): Whether to exclude private modules

    Returns:
        list: List of (module, module_name) tuples
    """
    modules_to_process = []

    # Process the root module
    if hasattr(package, "__file__") and package.__file__:
        modules_to_process.append((package, package.__name__))
        logger.debug(f"Added root module: {package.__name__} from {package.__file__}")

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

        logger.debug(f"Scanning for submodules in {current_name}, path: {current_package.__path__}")

        for _module_finder, module_name, is_pkg in pkgutil.iter_modules(current_package.__path__, f"{current_name}."):
            logger.debug(f"Found submodule: {module_name}, is_package: {is_pkg}")

            if exclude_private and any(part.startswith("_") for part in module_name.split(".")):
                logger.debug(f"Skipping private module: {module_name}")
                continue

            try:
                module = importlib.import_module(module_name)
                if hasattr(module, "__file__") and module.__file__:
                    modules_to_process.append((module, module_name))
                    logger.debug(f"Added module: {module_name} from {module.__file__}")

                    # If this is a package, add it to the exploration queue
                    if is_pkg:
                        modules_to_explore.append((module, module_name))
            except (ImportError, AttributeError):
                logger.exception(f"Failed to import module {module_name}")

    logger.debug(f"Collected {len(modules_to_process)} modules in total")
    return modules_to_process


def group_modules_by_file(
    modules: list[tuple[object, str]],
) -> dict[str, list[tuple[object, str]]]:
    """Group modules by their file path.

    Args:
        modules (list): List of (module, module_name) tuples

    Returns:
        dict: Dictionary mapping file paths to lists of (module, module_name) tuples
    """
    file_to_modules = defaultdict(list)

    for module, module_name in modules:
        if hasattr(module, "__file__") and module.__file__:
            file_to_modules[module.__file__].append((module, module_name))

    return file_to_modules


def has_documentable_members(
    module: object,
    *,
    exclude_private: bool,
) -> bool:
    """Check if a module has documentable members.

    Args:
        module (object): Module to check
        exclude_private (bool): Whether to exclude private members

    Returns:
        bool: True if the module has documentable members
    """
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


def process_module_file(config: ModuleFileConfig) -> bool:
    """Process a module file and generate documentation.

    Args:
        config: Configuration for processing the module file

    Returns:
        bool: True if processing was successful, False otherwise
    """
    try:
        # Get the file name without extension
        path_obj = Path(config.file_path)
        file_name = path_obj.stem

        logger.debug(f"Processing {config.file_path}, stem: {file_name}")

        # Skip __init__ files with no content
        if file_name == "__init__" and not has_documentable_members(
            config.modules[0][0],
            exclude_private=config.exclude_private,
        ):
            logger.debug(f"Skipping empty __init__ file: {config.file_path}")
            return False

        # Determine the module path for directory structure
        # Use the module with the shortest name to determine the path
        module, module_name = min(config.modules, key=lambda x: len(x[1]))
        logger.debug(f"Using module {module_name} for path structure")

        # Split the module name to get the path components
        parts = module_name.split(".")
        logger.debug(f"Module path parts: {parts}")

        # Extract the path components excluding the root package and current module name
        # First component is the package name, last component is often the module name
        if len(parts) > 1:
            # Extract everything except the first component (root package)
            simplified_path = parts[1:]

            # If the last component matches the file_name, remove it
            if simplified_path and simplified_path[-1] == file_name:
                simplified_path = simplified_path[:-1]

            # Also remove any __init__ components
            simplified_path = [part for part in simplified_path if part != "__init__"]
        else:
            simplified_path = []

        logger.debug(f"Simplified path: {simplified_path}")

        # Create the output directory path
        module_dir = config.output_dir
        if simplified_path:
            module_dir = config.output_dir.joinpath(*simplified_path)
            logger.debug(f"Creating directory: {module_dir}")
            module_dir.mkdir(exist_ok=True, parents=True)
        else:
            logger.debug(f"Using root directory: {module_dir}")

        # Generate content
        try:
            # Wrap the generation in a try-except block to handle issues
            content = config.converter_func(
                module,
                module_name,
                github_repo=config.github_config.github_repo if config.github_config else None,
                branch=config.github_config.branch if config.github_config else "main",
            )

            # Create the Next.js page structure
            page_path = module_dir / file_name
            page_path.mkdir(exist_ok=True, parents=True)

            # Write to file with specified extension
            output_file = page_path / f"page{config.output_extension}"
            logger.debug(f"Writing to file: {output_file}")
            output_file.write_text(content)
            return True
        except (ValueError, TypeError, AttributeError, ImportError):
            logger.exception(f"Failed to generate documentation for module {module_name}")
            return False
    except (ValueError, TypeError, AttributeError, ImportError, OSError):
        logger.exception(f"Error processing file {config.file_path}")
        return False


def package_to_structure(config: PackageConfig) -> None:
    """Convert installed package to documentation files with directory structure.

    This function imports the package, detects all modules and submodules, and
    generates documentation for each file, while preserving the directory structure.
    Progress is reported with a tqdm progress bar.

    Args:
        config: Configuration for processing the package
    """
    # Create GitHub config
    github_config = GitHubConfig(github_repo=config.github_repo, branch=config.branch)

    try:
        # Import the package
        package = importlib.import_module(config.package_name)
        config.output_dir.mkdir(exist_ok=True, parents=True)

        # Collect all modules in the package
        logger.info(f"Collecting modules in {config.package_name}...")
        modules_to_process = collect_package_modules(
            package,
            config.package_name,
            exclude_private=config.exclude_private,
        )

        # Debug output for modules collected
        logger.debug(f"Total modules collected: {len(modules_to_process)}")
        for module, module_name in modules_to_process:
            logger.debug(f"Module: {module_name} from {getattr(module, '__file__', 'Unknown file')}")

        # Group modules by file
        file_to_modules = group_modules_by_file(modules_to_process)

        # Debug output for file grouping
        logger.debug(f"Total files to process: {len(file_to_modules)}")
        for file_path, modules in file_to_modules.items():
            logger.debug(f"File: {file_path} with {len(modules)} modules")
            for _module, module_name in modules:
                logger.debug(f"  - Module: {module_name}")

        # Process each file and generate documentation
        logger.info(f"Processing {len(file_to_modules)} files...")
        success_count = 0
        error_count = 0

        for file_path, modules in tqdm(file_to_modules.items(), desc=config.progress_desc):
            logger.debug(f"Processing file: {file_path}")
            try:
                module_config = ModuleFileConfig(
                    file_path=file_path,
                    modules=modules,
                    output_dir=config.output_dir,
                    exclude_private=config.exclude_private,
                    github_config=github_config,
                    converter_func=config.converter_func,
                    output_extension=config.output_extension,
                )
                if process_module_file(module_config):
                    success_count += 1
                else:
                    error_count += 1
            except (ValueError, TypeError, AttributeError, ImportError, OSError):
                logger.exception(f"Error processing file {file_path}")
                error_count += 1

        logger.info(
            f"Documentation generation complete. Processed {len(file_to_modules)} files: "
            f"{success_count} successful, {error_count} with errors.",
        )

    except ImportError:
        logger.exception(f"Could not import package '{config.package_name}'")
    except (ValueError, TypeError, AttributeError):
        logger.exception(f"Error processing package '{config.package_name}'")
