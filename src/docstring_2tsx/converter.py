"""Utilities for converting Google-style docstrings to TSX.

This module provides functions to convert Python classes and functions with Google-style
docstrings into TSX documentation components.
"""

import inspect
import logging
from collections.abc import Callable
from pathlib import Path

from google_docstring_parser import parse_google_docstring

from utils.processor import (
    build_params_table,
    process_description,
    process_other_sections,
)
from utils.shared import (
    collect_package_modules,
    group_modules_by_file,
    has_documentable_members,
    process_module_file,
)
from utils.signature_formatter import format_signature, get_signature_params

logger = logging.getLogger(__name__)


def get_source_line(obj: type | Callable) -> int:
    """Get the source line number for an object.

    Args:
        obj: Class or function to get source line for

    Returns:
        Line number where the object is defined
    """
    try:
        return inspect.getsourcelines(obj)[1]
    except (OSError, TypeError):
        # If we can't get the source line, return 1 as a fallback
        return 1


def class_to_tsx(obj: type | Callable, *, github_repo: str | None = None, branch: str = "main") -> str:
    """Convert class or function to TSX component.

    This function generates TSX documentation component for a class or function,
    extracting information from its docstring and signature.

    Args:
        obj (Union[type, Callable]): Class or function to document
        github_repo (str | None): Base URL of the GitHub repository (e.g., "https://github.com/username/repo")
        branch (str): The branch name to link to (default: "main")

    Returns:
        TSX component as string
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
            f"<h1>{obj_name}</h1>",
            f"<pre><code className='language-python'>{signature}</code></pre>",
        ],
    )

    # Add GitHub link if github_repo is provided
    if github_repo:
        source_line = get_source_line(obj)
        # GitHub icon SVG path split into smaller chunks
        svg_path = (
            "M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-"
            "2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87"
            ".87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-"
            "2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1."
            "92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2"
            " 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"
        )
        github_icon = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" '
            f'fill="currentColor"><path d="{svg_path}"/></svg>'
        )
        github_link = (
            f'<a href="{github_repo}/blob/{branch}/{obj.__module__.replace(".", "/")}.py#L{source_line}" '
            'className="github-source-link">View source on GitHub</a>'
        )
        sections.append(
            f'<div className="github-source-container">'
            f'<span className="github-icon">{github_icon}</span>'
            f"{github_link}"
            f"</div>",
        )

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

    # Wrap everything in a TSX component
    return f"""import React from 'react';

export default function {obj_name}() {{
  return (
    <div className="docstring-content">
      {" ".join(sections)}
    </div>
  );
}}
"""


def module_to_tsx_files(
    module: object,
    output_dir: Path,
    *,
    exclude_private: bool = False,
    github_repo: str | None = None,
    branch: str = "main",
) -> None:
    """Generate TSX files for all classes and functions in a module.

    Args:
        module (object): Python module
        output_dir (Path): Directory to write TSX files
        exclude_private (bool): Whether to exclude private classes and methods
        github_repo (str | None): Base URL of the GitHub repository
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
                tsx = class_to_tsx(obj, github_repo=github_repo, branch=branch)
                output_file = output_dir / f"{name}.tsx"
                output_file.write_text(tsx)
            except (ValueError, TypeError, AttributeError):
                logger.exception("Error processing %s", name)


def package_to_tsx_files(
    package: object,
    output_dir: Path,
    *,
    exclude_private: bool = True,
    github_repo: str | None = None,
    branch: str = "main",
) -> None:
    """Generate TSX files for all modules in a package.

    Args:
        package (object): Python package
        output_dir (Path): Directory to write TSX files
        exclude_private (bool): Whether to exclude private modules (starting with _)
        github_repo (str | None): Base URL of the GitHub repository
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
                converter_func=class_to_tsx,
            )

            # Write the content to a file
            output_file = output_dir / f"{module_name.replace('.', '_')}.tsx"
            output_file.write_text(content)
        except Exception:
            logger.exception("Error processing file %s", file_path)
