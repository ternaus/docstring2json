"""Utilities for processing Google-style docstrings into structured data format.

This module provides functions for converting docstring sections into structured data
that can be used with TSX components.
"""

import logging

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
            "type": param_docs.get(param.name, {}).get("type", param.type or ""),
            "description": param_docs.get(param.name, {}).get("description", ""),
        }
        result.append(param_dict)

    return result


def _format_returns_data(content: dict | None) -> dict | None:
    """Format the Returns section as data.

    Args:
        content: Section content from google_docstring_parser

    Returns:
        Dictionary with return type and description or None if no content
    """
    if not content:
        return None

    return {
        "type": content.get("type"),
        "description": content.get("description", ""),
    }


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

    section_formatters = {
        "Returns": lambda c: {"title": "Returns", "content": _format_returns_data(c), "contentType": "data"},
        "Raises": lambda c: {"title": "Raises", "content": _format_raises_data(c), "contentType": "data"},
        "Example": lambda c: {"title": "Example", "content": c, "contentType": "code"},
        "References": lambda c: {
            "title": "References",
            "content": c,  # google_docstring_parser already gives us the correct format
            "contentType": "reference",
        },
    }

    formatter = section_formatters.get(section)
    if formatter:
        logger.debug(f"Using formatter for section {section} with content: {content}")
        return formatter(content)

    # Default format for other sections
    return {
        "title": section,
        "content": content,
        "contentType": "text",
    }
