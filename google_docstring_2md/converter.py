"""Utilities for converting Google-style docstrings to Markdown.

This module provides functions to convert Python classes and functions with Google-style
docstrings into Markdown documentation.
"""

import importlib
import inspect
import logging
import pkgutil
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from google_docstring_parser import parse_google_docstring

from google_docstring_2md.docstring_processor import (
    build_params_table,
    process_description,
    process_other_sections,
)
from google_docstring_2md.github_linker import GitHubConfig, add_github_link
from google_docstring_2md.signature_formatter import format_signature, get_signature_params

logger = logging.getLogger(__name__)


def class_to_markdown(obj: type | Callable, *, github_repo: str | None = None, branch: str = "main") -> str:
    """Convert class or function to markdown documentation.

    This function generates markdown documentation for a class or function,
    extracting information from its docstring and signature.

    Args:
        obj (Union[type, Callable]): Class or function to document
        github_repo (str | None): Base URL of the GitHub repository (e.g., "https://github.com/username/repo")
        branch (str): The branch name to link to (default: "main")

    Returns:
        Markdown formatted documentation string
    """
    sections = []

    # Get object name and parameters
    obj_name = obj.__name__
    params = get_signature_params(obj)

    # Format and add the signature
    signature = format_signature(obj, params)

    # Add the object name and signature
    sections.extend(
        [
            f"# {obj_name}\n",
            f"```python\n{signature}\n```\n",
        ],
    )

    # Add GitHub link if github_repo is provided
    add_github_link(sections, obj, github_repo, branch)

    # Parse docstring
    docstring = obj.__doc__ or ""
    parsed = parse_google_docstring(docstring)

    # Add description
    description = process_description(parsed)
    if description:
        sections.append(description)

    # Add parameters table if we have parameters
    if params:
        param_table = build_params_table(params, parsed, obj)
        sections.extend(param_table)

    # Add remaining sections
    other_sections = process_other_sections(parsed)
    sections.extend(other_sections)

    return "".join(sections)


def module_to_markdown_files(
    module: object,
    output_dir: Path,
    *,
    exclude_private: bool = False,
    github_repo: str | None = None,
    branch: str = "main",
) -> None:
    """Generate markdown files for all classes and functions in a module.

    Args:
        module (object): Python module
        output_dir (Path): Directory to write markdown files
        exclude_private (bool): Whether to exclude private classes and methods (starting with _)
        github_repo (str | None): Base URL of the GitHub repository (e.g., "https://github.com/username/repo")
        branch (str): The branch name to link to (default: "main")
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process classes and functions
    for name, obj in inspect.getmembers(module):
        # Skip private members if exclude_private is True
        if exclude_private and name.startswith("_"):
            continue

        # Only consider classes and functions defined in this module
        # or directly assigned to this module
        if (hasattr(obj, "__module__") and obj.__module__ == module.__name__) or (
            inspect.isclass(obj) or inspect.isfunction(obj)
        ):
            try:
                markdown = class_to_markdown(obj, github_repo=github_repo, branch=branch)
                output_file = output_dir / f"{name}.mdx"
                output_file.write_text(markdown)
            except (ValueError, TypeError, AttributeError):
                logger.exception("Error processing %s", name)


def _collect_module_members(module: object) -> tuple[list[tuple[str, object]], list[tuple[str, object]]]:
    """Collect classes and functions from a module.

    Args:
        module (object): Module to process

    Returns:
        Tuple containing lists of (name, object) pairs for classes and functions
    """
    classes = []
    functions = []

    for name, obj in inspect.getmembers(module):
        if name.startswith("_"):
            continue

        if hasattr(obj, "__module__") and obj.__module__ == module.__name__:
            if inspect.isclass(obj):
                classes.append((name, obj))
            elif inspect.isfunction(obj):
                functions.append((name, obj))

    return classes, functions


def _normalize_anchor_id(module_name: str, name: str) -> str:
    """Normalize anchor ID for consistent markdown navigation.

    Args:
        module_name (str): Module name
        name (str): Object name

    Returns:
        str: Normalized anchor ID with dots replaced by hyphens
    """
    anchor_id = f"{module_name}.{name}"
    return anchor_id.replace(".", "-")


def _build_table_of_contents(classes: list[tuple[str, object]], functions: list[tuple[str, object]]) -> str:
    """Build a table of contents for the markdown document.

    Args:
        classes (list): List of (name, object) pairs for classes
        functions (list): List of (name, object) pairs for functions

    Returns:
        Markdown formatted table of contents
    """
    toc = ["# Table of Contents\n\n"]

    # Add classes to ToC
    for name, obj in sorted(classes):
        module_name = obj.__module__
        anchor_id = _normalize_anchor_id(module_name, name)
        toc.append(f"* [{name}](#{anchor_id})\n")

    # Add functions to ToC
    for name, obj in sorted(functions):
        module_name = obj.__module__
        anchor_id = _normalize_anchor_id(module_name, name)
        toc.append(f"* [{name}](#{anchor_id})\n")

    toc.append("\n")
    return "".join(toc)


def _process_documentation_items(
    items: list[tuple[str, object]],
    section_title: str,
    *,
    github_repo: str | None = None,
    branch: str = "main",
) -> str:
    """Process a list of documentation items (classes or functions).

    Args:
        items (list): List of (name, object) pairs to document
        section_title (str): Section title (e.g., "Classes" or "Functions")
        github_repo (str | None): Base URL of the GitHub repository (e.g., "https://github.com/username/repo")
        branch (str): The branch name to link to (default: "main")

    Returns:
        Markdown formatted documentation for the items
    """
    if not items:
        return ""

    content = [f"**{section_title}**\n\n"]

    for name, obj in sorted(items):
        md = class_to_markdown(obj, github_repo=github_repo, branch=branch)

        # Add anchor for the item
        module_name = obj.__module__
        anchor_id = _normalize_anchor_id(module_name, name)
        content.append(f'<a id="{anchor_id}"></a>\n\n')

        # Adjust heading level
        lines = md.split("\n")
        if lines and lines[0].startswith("# "):
            lines[0] = f"## {lines[0][2:]}"

        content.append("\n".join(lines) + "\n\n")

    return "".join(content)


def file_to_markdown(module: object, module_name: str, *, github_repo: str | None = None, branch: str = "main") -> str:
    """Convert a module to a single markdown document.

    Args:
        module (object): The module object to document
        module_name (str): Name of the module for the heading
        github_repo (str | None): Base URL of the GitHub repository (e.g., "https://github.com/username/repo")
        branch (str): The branch name to link to (default: "main")

    Returns:
        str: The markdown content
    """
    # Collect module members
    classes, functions = _collect_module_members(module)

    # Normalize the module_name for the anchor
    module_anchor = module_name.replace(".", "-")

    content = [
        f"# {module_name}\n\n",
        _build_table_of_contents(classes, functions),
        f'<a id="{module_anchor}"></a>\n\n',
        f"# {module_name}\n\n",
    ]

    # Add class documentation
    content.append(_process_documentation_items(classes, "Classes", github_repo=github_repo, branch=branch))

    # Add function documentation
    content.append(_process_documentation_items(functions, "Functions", github_repo=github_repo, branch=branch))

    return "".join(content)


def _process_mock_package(
    package: object,
    package_name: str,
    output_dir: Path,
    *,
    exclude_private: bool,
    github_config: GitHubConfig | None = None,
) -> None:
    """Process a mock package that doesn't have a __path__ attribute.

    Args:
        package (object): The package object
        package_name (str): Name of the package
        output_dir (Path): Root directory for output
        exclude_private (bool): Whether to exclude private classes and methods
        github_config (GitHubConfig | None): Configuration for GitHub integration
    """
    if github_config is None:
        github_config = GitHubConfig()

    logger.info(f"Processing mock package {package_name}")
    # Process the root module directly
    module_to_markdown_files(
        package,
        output_dir,
        exclude_private=exclude_private,
        github_repo=github_config.github_repo,
        branch=github_config.branch,
    )

    # Check if there are submodules as direct attributes
    for _name, obj in inspect.getmembers(package):
        if inspect.ismodule(obj) and obj.__name__.startswith(f"{package_name}."):
            # Create subdirectory for submodule
            rel_name = obj.__name__[len(package_name) + 1 :]
            sub_dir = output_dir / rel_name
            sub_dir.mkdir(exist_ok=True, parents=True)
            module_to_markdown_files(
                obj,
                sub_dir,
                exclude_private=exclude_private,
                github_repo=github_config.github_repo,
                branch=github_config.branch,
            )


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
    github_config: GitHubConfig | None = None,
) -> bool:
    """Process a module file and generate markdown documentation.

    Args:
        file_path (str): Path to the module file
        modules (list): List of (module, module_name) tuples for this file
        output_dir (Path): Root directory for output
        exclude_private (bool): Whether to exclude private classes and methods
        github_config (GitHubConfig | None): Configuration for GitHub integration

    Returns:
        bool: True if the process was successful, False otherwise
    """
    if github_config is None:
        github_config = GitHubConfig()

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
            return False

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
            md_content = file_to_markdown(
                module,
                module_name,
                github_repo=github_config.github_repo,
                branch=github_config.branch,
            )

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


def package_to_markdown_structure(
    package_name: str,
    output_dir: Path,
    *,
    exclude_private: bool = False,
    github_repo: str | None = None,
    branch: str = "main",
) -> None:
    """Convert installed package to markdown files with directory structure.

    This function imports the package, detects all modules and submodules, and
    generates markdown documentation for each file, while preserving the directory structure.
    Progress is reported with a tqdm progress bar.

    Args:
        package_name (str): Name of installed package
        output_dir (Path): Root directory for output markdown files
        exclude_private (bool): Whether to exclude private classes and methods (starting with _)
        github_repo (str | None): Base URL of the GitHub repository (e.g., "https://github.com/username/repo")
        branch (str): The branch name to link to (default: "main")
    """
    # Create GitHub config
    github_config = GitHubConfig(github_repo=github_repo, branch=branch)

    try:
        # Import the package
        package = importlib.import_module(package_name)
        output_dir.mkdir(exist_ok=True, parents=True)

        # Special handling for test mock packages that don't have __path__
        if not hasattr(package, "__path__"):
            _process_mock_package(
                package,
                package_name,
                output_dir,
                exclude_private=exclude_private,
                github_config=github_config,
            )
            return

        # Collect all modules in the package
        logger.info(f"Collecting modules in {package_name}...")
        modules_to_process = _collect_package_modules(package, package_name, exclude_private=exclude_private)

        # Group modules by file
        file_to_modules = _group_modules_by_file(modules_to_process)

        # Process each file and generate markdown
        logger.info(f"Processing {len(file_to_modules)} files...")
        success_count = 0
        error_count = 0

        def _safe_process_module_file(file_path: str, modules: list[tuple[object, str]]) -> bool:
            try:
                return _process_module_file(
                    file_path,
                    modules,
                    output_dir,
                    exclude_private=exclude_private,
                    github_config=github_config,
                )
            except (ValueError, TypeError, AttributeError, ImportError, OSError):
                logger.exception(f"Error processing file {file_path}")
                return False

        for file_path, modules in file_to_modules.items():
            result = _safe_process_module_file(file_path, modules)
            if result:
                success_count += 1
            else:
                error_count += 1

        logger.info(
            f"Documentation generation complete. Processed {len(file_to_modules)} files: "
            f"{success_count} successful, {error_count} with errors.",
        )

    except ImportError:
        logger.exception(f"Could not import package '{package_name}'")
    except (ValueError, TypeError, AttributeError):
        logger.exception(f"Error processing package '{package_name}'")
