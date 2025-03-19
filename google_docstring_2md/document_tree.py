"""Utilities for organizing Python documentation into a tree structure.

This module provides functions to convert Python packages into a structured tree
of Markdown/MDX documentation files, preserving the original package structure.
"""

import importlib
import inspect
import logging
import os
import pkgutil
from collections import defaultdict
from pathlib import Path

from tqdm import tqdm

from google_docstring_2md.converter import file_to_markdown, module_to_markdown_files

logger = logging.getLogger(__name__)


def _process_mock_package(
    package: object,
    package_name: str,
    output_dir: Path,
    *,
    exclude_private: bool,
) -> None:
    """Process a mock package that doesn't have a __path__ attribute.

    Args:
        package (object): The package object
        package_name (str): Name of the package
        output_dir (Path): Root directory for output
        exclude_private (bool): Whether to exclude private classes and methods
    """
    logger.info(f"Processing mock package {package_name}")
    # Process the root module directly
    module_to_markdown_files(package, output_dir, exclude_private=exclude_private)

    # Check if there are submodules as direct attributes
    for _name, obj in inspect.getmembers(package):
        if inspect.ismodule(obj) and obj.__name__.startswith(package_name + "."):
            # Create subdirectory for submodule
            rel_name = obj.__name__[len(package_name) + 1 :]
            sub_dir = output_dir / rel_name
            sub_dir.mkdir(exist_ok=True, parents=True)
            module_to_markdown_files(obj, sub_dir, exclude_private=exclude_private)


def _collect_package_modules(
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

        for _module_finder, module_name, is_pkg in pkgutil.iter_modules(current_package.__path__, current_name + "."):
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


def _group_modules_by_file(
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


def _has_documentable_members(
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


def _process_module_file(
    file_path: str,
    modules: list[tuple[object, str]],
    output_dir: Path,
    *,
    exclude_private: bool,
) -> None:
    """Process a module file and generate markdown documentation.

    Args:
        file_path (str): Path to the module file
        modules (list): List of (module, module_name) tuples for this file
        output_dir (Path): Root directory for output
        exclude_private (bool): Whether to exclude private classes and methods
    """
    try:
        # Get the file name without extension
        path_obj = Path(file_path)
        file_name = path_obj.stem

        logger.debug(f"Processing {file_path}, stem: {file_name}")

        # Skip __init__ files with no content
        if file_name == "__init__" and not _has_documentable_members(
            modules[0][0],
            exclude_private=exclude_private,
        ):
            logger.debug(f"Skipping empty __init__ file: {file_path}")
            return None

        # Determine the module path for directory structure
        # Use the module with the shortest name to determine the path
        module, module_name = min(modules, key=lambda x: len(x[1]))
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
        module_dir = output_dir
        if simplified_path:
            module_dir = output_dir.joinpath(*simplified_path)
            logger.debug(f"Creating directory: {module_dir}")
            module_dir.mkdir(exist_ok=True, parents=True)
        else:
            logger.debug(f"Using root directory: {module_dir}")

        # Generate markdown content
        try:
            # Wrap the markdown generation in a try-except block to handle issues
            md_content = file_to_markdown(module, module_name)

            # Write to file with .mdx extension
            output_file = module_dir / f"{file_name}.mdx"
            logger.debug(f"Writing to file: {output_file}")
            output_file.write_text(md_content)
        except (ValueError, TypeError, AttributeError, ImportError):
            logger.exception(f"Failed to generate markdown for module {module_name}")
            return False
        else:
            return True
    except (ValueError, TypeError, AttributeError, ImportError, OSError):
        logger.exception(f"Error processing file {file_path}")
        return False


def _generate_module_index_files(output_dir: Path) -> None:
    """Generate index files for modules and submodules.

    This function walks through the output directory structure and creates index.mdx files
    for each directory, listing all the available documentation files.

    Args:
        output_dir (Path): Root directory of the generated documentation
    """
    logger.info("Generating module index files...")

    # Process each directory in the output
    for root, dirs, files in os.walk(output_dir):
        root_path = Path(root)
        rel_path = root_path.relative_to(output_dir)

        # Skip the root directory, we'll handle it separately
        if root_path == output_dir:
            continue

        # Get module name from relative path
        module_name = str(rel_path).replace(os.path.sep, ".")

        # Get all .mdx files, excluding any existing index.mdx
        mdx_files = [f for f in files if f.endswith(".mdx") and f != "index.mdx"]

        # Get directory name for creating properly qualified links
        # This is needed for Docusaurus to resolve links correctly
        dir_name = root_path.name

        # Create links for each file - with fully qualified path for Docusaurus
        links = [f"- [{file[:-4]}]({dir_name}/{file[:-4]})" for file in sorted(mdx_files)]

        # Create links for each subdirectory - with fully qualified path for Docusaurus
        # Each subdirectory link should have the format: directory/subdirectory
        links.extend([f"- [{subdir_name}]({dir_name}/{subdir_name})" for subdir_name in sorted(dirs)])

        # Only create an index file if there are links
        if links:
            # Create content for the index file
            content = [
                f"# {module_name}",
                "",
                "## Contents",
                "",
            ]
            content.extend(links)

            # Write the index file
            index_path = root_path / "index.mdx"
            index_path.write_text("\n".join(content))
            logger.debug(f"Created index file at {index_path}")

    # Create root index file
    _generate_root_index_file(output_dir)


def _generate_root_index_file(output_dir: Path) -> None:
    """Generate the root index file.

    Args:
        output_dir (Path): Root directory of the generated documentation
    """
    # Get direct subdirectories and files
    subdirs = [d for d in output_dir.iterdir() if d.is_dir()]
    files = [f for f in output_dir.iterdir() if f.is_file() and f.name.endswith(".mdx") and f.name != "index.mdx"]

    # Create links
    links = []

    # Add links to submodules first - at root level, links should be just the directory name
    links.extend([f"- [{subdir.name}]({subdir.name})" for subdir in sorted(subdirs)])

    # Add links to root level files
    links.extend([f"- [{file.stem}]({file.stem})" for file in sorted(files)])

    # Create content
    content = [
        "# API Documentation",
        "",
        "## Modules",
        "",
    ]
    content.extend(links)

    # Write the index file
    index_path = output_dir / "index.mdx"
    index_path.write_text("\n".join(content))
    logger.debug(f"Created root index file at {index_path}")


def package_to_markdown_structure(
    package_name: str,
    output_dir: Path,
    *,
    exclude_private: bool = False,
) -> None:
    """Convert installed package to markdown files with directory structure.

    This function imports the package, detects all modules and submodules, and
    generates markdown documentation for each file, while preserving the directory structure.
    Progress is reported with a tqdm progress bar.

    Args:
        package_name (str): Name of installed package
        output_dir (Path): Root directory for output markdown files
        exclude_private (bool): Whether to exclude private classes and methods (starting with _)
    """
    try:
        # Import the package
        package = importlib.import_module(package_name)
        output_dir.mkdir(exist_ok=True, parents=True)

        # Special handling for test mock packages that don't have __path__
        if not hasattr(package, "__path__"):
            _process_mock_package(package, package_name, output_dir, exclude_private=exclude_private)
            return

        # Collect all modules in the package
        logger.info(f"Collecting modules in {package_name}...")
        modules_to_process = _collect_package_modules(package, package_name, exclude_private=exclude_private)

        # Debug output for modules collected
        logger.debug(f"Total modules collected: {len(modules_to_process)}")
        for module, module_name in modules_to_process:
            logger.debug(f"Module: {module_name} from {getattr(module, '__file__', 'Unknown file')}")

        # Group modules by file
        file_to_modules = _group_modules_by_file(modules_to_process)

        # Debug output for file grouping
        logger.debug(f"Total files to process: {len(file_to_modules)}")
        for file_path, modules in file_to_modules.items():
            logger.debug(f"File: {file_path} with {len(modules)} modules")
            for _module, module_name in modules:
                logger.debug(f"  - Module: {module_name}")

        # Process each file and generate markdown
        logger.info(f"Processing {len(file_to_modules)} files...")
        success_count = 0
        error_count = 0

        for file_path, modules in tqdm(file_to_modules.items(), desc="Generating markdown"):
            logger.debug(f"Processing file: {file_path}")
            try:
                result = _process_module_file(file_path, modules, output_dir, exclude_private=exclude_private)
                if result:
                    success_count += 1
                else:
                    error_count += 1
            except (ValueError, TypeError, AttributeError, ImportError, OSError):
                logger.exception(f"Error processing file {file_path}")
                error_count += 1

        # Generate index files for all modules and submodules
        _generate_module_index_files(output_dir)

        logger.info(
            f"Documentation generation complete. Processed {len(file_to_modules)} files: "
            f"{success_count} successful, {error_count} with errors.",
        )

    except ImportError:
        logger.exception(f"Could not import package '{package_name}'")
    except (ValueError, TypeError, AttributeError):
        logger.exception(f"Error processing package '{package_name}'")
