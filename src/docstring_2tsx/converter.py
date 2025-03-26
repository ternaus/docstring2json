"""Utilities for converting Google-style docstrings to TSX.

This module provides functions to convert Python classes and functions with Google-style
docstrings into TSX documentation components.
"""

import logging
from collections.abc import Callable
from pathlib import Path

from google_docstring_parser import parse_google_docstring

from utils.github_linker import add_github_link
from utils.processor import (
    build_params_table,
    process_description,
    process_other_sections,
)
from utils.signature_formatter import format_signature, get_signature_params

logger = logging.getLogger(__name__)


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
    msg = "TSX file generation not yet implemented"
    raise NotImplementedError(msg)
