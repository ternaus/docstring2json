"""Utilities for processing Google-style docstrings into TSX format.

This module provides functions for converting docstring sections into TSX components.
"""

import re
from collections.abc import Callable

from utils.processor import (
    build_params_table,
    process_other_sections,
)
from utils.signature_formatter import Parameter


def escape_tsx_special_chars(text: str) -> str:
    """Escape special characters that might cause issues in TSX.

    Args:
        text (str): Text to escape

    Returns:
        str: Escaped text safe for TSX
    """
    if not text:
        return text

    # Escape characters that might cause parsing issues in TSX
    escaped = text.replace("<", "&lt;").replace(">", "&gt;").replace("=", "&equals;")

    # Replace multiple backslashes (e.g. \\n) with a code format
    escaped = re.sub(r"\\{2,}", lambda m: f"`{m.group(0)}`", escaped)

    # Escape curly braces, which are special in JSX
    return escaped.replace("{", "&lbrace;").replace("}", "&rbrace;")


def process_description(parsed: dict) -> str:
    """Process description section from parsed docstring.

    Args:
        parsed (dict): Parsed docstring dictionary

    Returns:
        Formatted description as TSX component
    """
    if "Description" not in parsed:
        return ""

    desc = parsed["Description"]
    if not isinstance(desc, str):
        desc = str(desc)

    # Escape special characters in the description
    desc = escape_tsx_special_chars(desc)

    return f"<p>{desc}</p>"


def extract_param_docs(param: Parameter, param_docs: dict, obj: type | Callable) -> tuple[str, str]:
    """Extract parameter documentation info.

    Args:
        param (Parameter): Parameter object
        param_docs (dict): Dictionary mapping parameter names to docstring info
        obj (Union[type, Callable]): Class or function object

    Returns:
        Tuple of (type, description)
    """
    doc_type = param.type
    desc = param_docs.get(param.name, {}).get("description", "")

    # If no type found in docstring, check annotations
    if not doc_type and param.name in obj.__annotations__:
        annotation = obj.__annotations__[param.name]
        if hasattr(annotation, "__name__"):
            doc_type = annotation.__name__
        else:
            doc_type = str(annotation).replace("typing.", "")
            if "'" in doc_type:
                doc_type = doc_type.split("'")[1]

    return doc_type, desc


def format_tsx_section(section: str, content: str) -> str:
    """Format section content for TSX.

    Args:
        section (str): Section name (e.g. "Examples", "Notes")
        content (str): Raw section content

    Returns:
        Formatted content as TSX component
    """
    # For now, we'll use the same formatting as MDX
    # In the future, we can add TSX-specific formatting
    return process_other_sections({section: content})[0]


def build_tsx_params_table(params: list, parsed: dict, obj: type | Callable) -> str:
    """Build a parameters table for TSX.

    Args:
        params (list): List of parameter objects from signature
        parsed (dict): Parsed docstring dictionary
        obj (Union[type, Callable]): Class or function object

    Returns:
        TSX component for parameters table
    """
    # For now, we'll use the same table format as MDX
    # In the future, we can create a more TSX-friendly table component
    return "".join(build_params_table(params, parsed, obj))
