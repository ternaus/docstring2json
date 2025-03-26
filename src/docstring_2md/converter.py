"""Utilities for converting Google-style docstrings to Markdown.

This module provides functions to convert Python classes and functions with Google-style
docstrings into Markdown documentation.
"""

import inspect
import logging
from collections.abc import Callable
from pathlib import Path

from google_docstring_parser import parse_google_docstring

from docstring_2md.processor import (
    build_params_table,
    process_description,
    process_other_sections,
)
from utils.github_linker import add_github_link
from utils.shared import (
    collect_module_members,
    collect_package_modules,
    group_modules_by_file,
    has_documentable_members,
    normalize_anchor_id,
    process_module_file,
)
from utils.signature_formatter import format_signature, get_signature_params

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
        anchor_id = normalize_anchor_id(module_name, name)
        toc.append(f"* [{name}](#{anchor_id})\n")

    # Add functions to ToC
    for name, obj in sorted(functions):
        module_name = obj.__module__
        anchor_id = normalize_anchor_id(module_name, name)
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
        anchor_id = normalize_anchor_id(module_name, name)
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
    classes, functions = collect_module_members(module)

    # Normalize the module_name for the anchor
    module_anchor = module_name.replace(".", "-")

    content = [
        f"# {module_name}\n\n",
        _build_table_of_contents(classes, functions),
        f'<a id="{module_anchor}"></a>\n\n',
    ]

    # Process classes and functions
    content.append(_process_documentation_items(classes, "Classes", github_repo=github_repo, branch=branch))
    content.append(_process_documentation_items(functions, "Functions", github_repo=github_repo, branch=branch))

    return "".join(content)


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


def package_to_markdown_files(
    package: object,
    output_dir: Path,
    *,
    exclude_private: bool = True,
    github_repo: str | None = None,
    branch: str = "main",
) -> None:
    """Generate markdown files for all modules in a package.

    Args:
        package (object): Python package
        output_dir (Path): Directory to write markdown files
        exclude_private (bool): Whether to exclude private modules (starting with _)
        github_repo (str | None): Base URL of the GitHub repository (e.g., "https://github.com/username/repo")
        branch (str): The branch name to link to (default: "main")
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect all modules in the package
    modules = collect_package_modules(package, exclude_private=exclude_private)

    # Group modules by file
    module_groups = group_modules_by_file(modules)

    # Process each file
    for file_path, file_modules in module_groups.items():
        if not has_documentable_members(file_modules[0][1]):
            continue

        try:
            # Get the module name from the first module in the file
            module_name = file_modules[0][1].__name__

            # Process the file
            content = process_module_file(
                file_path,
                file_modules,
                github_repo=github_repo,
                branch=branch,
                converter_func=file_to_markdown,
            )

            # Write the content to a file
            output_file = output_dir / f"{module_name.replace('.', '_')}.mdx"
            output_file.write_text(content)
        except Exception:
            logger.exception("Error processing file %s", file_path)
