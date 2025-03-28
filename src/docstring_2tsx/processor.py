"""Utilities for processing Google-style docstrings into structured data format.

This module provides functions for converting docstring sections into structured data
that can be used with TSX components.
"""

import logging

from utils.reference_parser import parse_references
from utils.signature_formatter import Parameter

logger = logging.getLogger(__name__)


def process_description(parsed: dict) -> str | None:
    """Process the description section.

    Args:
        parsed: Parsed docstring dictionary

    Returns:
        Processed description or None if not available
    """
    description = parsed.get("Description", "")
    if not description:
        return None

    return description


def build_params_data(params: list[Parameter], parsed: dict) -> list[dict] | None:
    """Build parameters data structure.

    Args:
        params: List of Parameter objects
        parsed: Parsed docstring dictionary

    Returns:
        List of parameter dictionaries or None if no parameters
    """
    if not params:
        return None

    param_docs = {}
    for param_entry in parsed.get("Args", []):
        param_docs[param_entry["name"]] = param_entry

    result = []
    for param in params:
        param_dict = {
            "name": param.name,
            "type": param.type or "",
            "description": param_docs.get(param.name, {}).get("description", ""),
        }
        result.append(param_dict)

    return result


def _format_returns_data(content: list | dict | str) -> dict | None:
    """Format the Returns section as data.

    Args:
        content: Section content

    Returns:
        Dictionary with return type and description
    """
    if not content:
        return None

    if isinstance(content, list) and len(content) > 0:
        return_info = content[0]
    elif isinstance(content, dict):
        return_info = content
    else:
        return {"type": "", "description": str(content)}

    if isinstance(return_info, dict):
        return {
            "type": return_info.get("type", ""),
            "description": return_info.get("description", ""),
        }
    return {"type": "", "description": str(return_info)}


def _format_raises_data(content: list | str) -> list[dict] | None:
    """Format the Raises section as data.

    Args:
        content: Section content

    Returns:
        List of dictionaries with exception type and description
    """
    if not content:
        return None

    raises_list = []
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                raises_list.append(
                    {
                        "type": item.get("type", ""),
                        "description": item.get("description", ""),
                    },
                )
            else:
                raises_list.append({"type": "", "description": str(item)})
    else:
        raises_list.append({"type": "", "description": str(content)})

    return raises_list if raises_list else None


def format_section_data(section: str, content: list | dict | str) -> dict | None:
    """Format a docstring section as structured data.

    Args:
        section: Section name
        content: Section content

    Returns:
        Dictionary with section data or None if no content
    """
    if not content:
        return None

    # Helper function to handle references parsing conditionally
    def process_references(c: str | list) -> list[dict] | list:
        return parse_references(c) if isinstance(c, str) else c

    section_formatters = {
        "Returns": lambda c: {"title": "Returns", "content": _format_returns_data(c), "contentType": "data"},
        "Raises": lambda c: {"title": "Raises", "content": _format_raises_data(c), "contentType": "data"},
        "Example": lambda c: {"title": "Example", "content": c, "contentType": "code"},
        "References": lambda c: {
            "title": "References",
            "content": process_references(c),
            "contentType": "reference",
        },
    }

    formatter = section_formatters.get(section)
    if formatter:
        return formatter(content)

    # Default format for other sections
    return {
        "title": section,
        "content": content,
        "contentType": "text",
    }
