"""Utilities for processing Google-style docstrings into TSX format.

This module provides functions for converting docstring sections into TSX components.
"""

import logging
import re
from collections.abc import Callable

from utils.reference_parser import format_references_section
from utils.signature_formatter import Parameter

logger = logging.getLogger(__name__)


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
    """Process the description section.

    Args:
        parsed: Parsed docstring dictionary

    Returns:
        Processed description as TSX
    """
    description = parsed.get("Description", "")
    if not description:
        return ""

    return f"<p>{description}</p>"


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


def build_tsx_params_table(params: list[Parameter], parsed: dict) -> list[str]:
    """Build a TSX table for function parameters.

    Args:
        params: List of Parameter objects
        parsed: Parsed docstring dictionary

    Returns:
        List of TSX strings for the parameters table
    """
    if not params:
        return []

    param_docs = {param["name"]: param["description"] for param in parsed.get("Args", [])}

    rows = []
    for param in params:
        type_str = param.type if param.type else ""
        description = param_docs.get(param.name, "")
        rows.append(
            f"<tr><td>{param.name}</td><td>{type_str}</td><td>{description}</td></tr>",
        )

    return [
        "<h3>Parameters</h3>",
        "<table>",
        "<thead><tr><th>Name</th><th>Type</th><th>Description</th></tr></thead>",
        "<tbody>",
        *rows,
        "</tbody>",
        "</table>",
    ]


def _format_returns_section(content: list | dict | str) -> str:
    """Format the Returns section.

    Args:
        content: Section content

    Returns:
        Formatted TSX string
    """
    if isinstance(content, list):
        return_info = content[0]
    elif isinstance(content, dict):
        return_info = content
    else:
        return f"<h3>Returns</h3><p>{content}</p>"

    type_str = return_info.get("type", "") if isinstance(return_info, dict) else ""
    desc = return_info.get("description", "") if isinstance(return_info, dict) else str(return_info)
    if type_str and desc:
        return f"<h3>Returns</h3><p><strong>{type_str}</strong>: {desc}</p>"
    if desc:
        return f"<h3>Returns</h3><p>{desc}</p>"
    return ""


def _format_raises_section(content: list | str) -> str:
    """Format the Raises section.

    Args:
        content: Section content

    Returns:
        Formatted TSX string
    """
    raises_list = []
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                type_str = item.get("type", "")
                desc = item.get("description", "")
            else:
                type_str = ""
                desc = str(item)
            if type_str and desc:
                raises_list.append(f"<li><strong>{type_str}</strong>: {desc}</li>")
            elif desc:
                raises_list.append(f"<li>{desc}</li>")
    else:
        raises_list.append(f"<li>{content}</li>")
    if raises_list:
        return f"<h3>Raises</h3><ul>{''.join(raises_list)}</ul>"
    return ""


def format_tsx_section(section: str, content: list | dict | str) -> str:
    """Format a docstring section as TSX.

    Args:
        section: Section name
        content: Section content

    Returns:
        Formatted section as TSX
    """
    if not content:
        return ""

    section_formatters = {
        "Returns": _format_returns_section,
        "Raises": _format_raises_section,
        "Example": lambda c: f"<h3>Example</h3><pre><code className='language-python'>{c}</code></pre>",
        "References": lambda c: (
            f"<h3>References</h3><ul>{format_references_section(c)}</ul>" if format_references_section(c) else ""
        ),
    }

    formatter = section_formatters.get(section)
    if formatter:
        return formatter(content)

    return f"<h3>{section}</h3><p>{content}</p>"
