"""Utilities for processing Google-style docstrings into TSX format.

This module provides functions for converting docstring sections into TSX components.
"""

import re
from collections.abc import Callable

from utils.reference_parser import format_references_section
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
        Formatted description as string
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


def build_tsx_params_table(params: list, parsed: dict) -> str:
    """Build a parameters table for TSX.

    Args:
        params: List of parameters
        parsed: Parsed docstring

    Returns:
        str: TSX formatted parameters table
    """
    if not params:
        return ""

    sections = [
        "<h2>Parameters</h2>",
        "<table>",
        "<thead>",
        "<tr>",
        "<th>Name</th>",
        "<th>Type</th>",
        "<th>Description</th>",
        "</tr>",
        "</thead>",
        "<tbody>",
    ]

    # Add each parameter
    parsed_params = parsed.get("Args", [])
    for param in params:
        param_doc = next((p for p in parsed_params if p["name"] == param.name), None)
        description = param_doc["description"] if param_doc else ""
        sections.extend(
            [
                "<tr>",
                f"<td><code>{param.name}</code></td>",
                f"<td><code>{param.type}</code></td>",
                f"<td>{escape_tsx_special_chars(description)}</td>",
                "</tr>",
            ],
        )

    sections.extend(["</tbody>", "</table>"])
    return "".join(sections)


def format_tsx_section(section: str, content: str) -> str:
    """Format section content for TSX.

    Args:
        section: Section name
        content: Section content

    Returns:
        str: Formatted TSX content
    """
    section_formatters = {
        "Returns": lambda c: f"<h3>Returns</h3><p>{c}</p>",
        "Raises": lambda c: f"<h3>Raises</h3><p>{c}</p>",
        "Example": lambda c: f"<h3>Example</h3><pre><code>{c}</code></pre>",
        "Examples": lambda c: f"<h3>Examples</h3><pre><code>{c}</code></pre>",
        "Note": lambda c: f"<div className='note'><h3>Note</h3><p>{c}</p></div>",
        "Warning": lambda c: f"<div className='warning'><h3>Warning</h3><p>{c}</p></div>",
        "References": lambda c: f"<h3>References</h3>{format_references_section(c)}",
    }

    formatter = section_formatters.get(section)
    if formatter:
        return formatter(content)

    # Default case for unknown sections
    return f"<h3>{section}</h3><p>{content}</p>"
