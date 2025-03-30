"""Utilities for processing docstrings.

This module provides functions for processing and formatting docstring sections
for documentation generation.
"""

from typing import Any

from utils.signature_formatter import Parameter


def process_description(parsed: dict[str, str | list[Any] | dict[str, Any]]) -> str | None:
    """Process description section from parsed docstring.

    Args:
        parsed: Parsed docstring data

    Returns:
        str | None: Processed description text from the Description section,
            or None if no description is found
    """
    description = parsed.get("Description")
    if isinstance(description, str):
        return description if description else None
    return None


def build_params_data(
    params: list[Parameter],
    parsed: dict[str, str | list[Any] | dict[str, Any]],
) -> list[dict[str, str]] | None:
    """Build parameters data structure.

    Args:
        params: List of parameter objects
        parsed: Parsed docstring data

    Returns:
        list[dict[str, str]] | None: List of parameter data dictionaries containing name,
            type, and description for each parameter, or None if no parameters are found
    """
    if not params:
        return None

    args_data = parsed.get("Args", [])
    if not args_data:
        return None

    result = []
    for param in params:
        param_data = next(
            (arg for arg in args_data if isinstance(arg, dict) and arg.get("name") == param.name),
            None,
        )
        if param_data and isinstance(param_data, dict):
            result.append(
                {
                    "name": param.name,
                    "type": param.type,
                    "description": param_data.get("description", ""),
                },
            )

    return result if result else None


def _format_returns_data(content: dict[str, str]) -> dict[str, str]:
    """Format returns data from docstring.

    Args:
        content: Returns section content

    Returns:
        dict[str, str]: Formatted returns data containing type and description
            of the return value
    """
    return {
        "type": content["type"],
        "description": content["description"],
    }


def _format_raises_data(content: list[dict[str, str]]) -> list[dict[str, str]]:
    """Format raises data from docstring.

    Args:
        content: Raises section content

    Returns:
        list[dict[str, str]]: List of formatted raises data, each containing type
            and description of the exception
    """
    return [
        {
            "type": item["type"],
            "description": item["description"],
        }
        for item in content
    ]


def format_section_data(section: str, content: str | dict[str, str] | list[dict[str, str]]) -> dict[str, Any] | None:
    """Format section data for documentation.

    Args:
        section: Section name
        content: Section content

    Returns:
        dict[str, Any] | None: Formatted section data containing title, content,
            and contentType, or None if content is empty. contentType can be:
            - "text" for regular sections
            - "code" for Example sections
            - "data" for Returns and Raises sections
    """
    if not content:
        return None

    result = {
        "title": section,
        "content": content,
        "contentType": "text",
    }

    if section == "Example":
        result["contentType"] = "code"
    elif section == "Returns" and isinstance(content, dict):
        result["content"] = _format_returns_data(content)
        result["contentType"] = "data"
    elif section == "Raises" and isinstance(content, list):
        result["content"] = _format_raises_data(content)
        result["contentType"] = "data"

    return result
