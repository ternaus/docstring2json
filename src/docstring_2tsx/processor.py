"""Utilities for processing Google-style docstrings into structured data format.

This module provides functions for converting docstring sections into structured data
that can be used with TSX components.
"""

import logging
from typing import TYPE_CHECKING, Any

from utils.signature_formatter import Parameter

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


def process_description(parsed: dict[str, str | list[Any] | dict[str, Any]]) -> str | None:
    """Process the description section.

    Args:
        parsed: Parsed docstring dictionary

    Returns:
        Processed description or None if not available
    """
    description = parsed.get("Description", "")
    if isinstance(description, str):
        return description if description else None
    return None


def build_params_data(params: list[Parameter], parsed: dict[str, list[dict[str, str]]]) -> list[dict[str, str]] | None:
    """Build parameters data structure.

    Args:
        params: List of Parameter objects
        parsed: Parsed docstring dictionary

    Returns:
        List of parameter dictionaries or None if no parameters
    """
    if not params:
        return None

    param_docs = {param_entry["name"]: param_entry for param_entry in parsed.get("Args", [])}

    result = []
    for param in params:
        param_dict = {
            "name": param.name,
            "type": param_docs.get(param.name, {}).get("type", param.type or ""),
            "description": param_docs.get(param.name, {}).get("description", ""),
        }
        result.append(param_dict)

    return result


def _format_returns_data(content: dict[str, str] | list[dict[str, str]] | None) -> dict[str, str] | None:
    """Format the Returns section as data.

    Args:
        content: Section content from google_docstring_parser

    Returns:
        Dictionary with return type and description or None if no content
    """
    if not content:
        return None

    if isinstance(content, list):
        if not content:
            return None
        content = content[0]

    if not isinstance(content, dict):
        return {"type": "", "description": str(content)}

    return {
        "type": content.get("type", ""),
        "description": content.get("description", ""),
    }


def _format_raises_data(content: list[dict[str, str] | str] | str) -> list[dict[str, str]] | None:
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

    return raises_list or None


def format_section_data(section: str, content: list[Any] | dict[str, Any] | str) -> dict[str, Any] | None:
    """Format a docstring section as structured data.

    Args:
        section: Section name
        content: Section content

    Returns:
        Dictionary with section data or None if no content
    """
    if not content:
        return None

    section_formatters: dict[str, Callable[[Any], dict[str, Any]]] = {
        "Returns": lambda c: {"title": "Returns", "content": _format_returns_data(c), "contentType": "data"},
        "Raises": lambda c: {"title": "Raises", "content": _format_raises_data(c), "contentType": "data"},
        "Example": lambda c: {"title": "Example", "content": c, "contentType": "code"},
        "References": lambda c: {
            "title": "References",
            "content": c,  # google_docstring_parser already gives us the correct format
            "contentType": "reference",
        },
    }

    if formatter := section_formatters.get(section):
        logger.debug(f"Using formatter for section {section} with content: {content}")
        return formatter(content)

    # Default format for other sections
    return {
        "title": section,
        "content": content,
        "contentType": "text",
    }
