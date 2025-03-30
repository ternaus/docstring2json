"""Utilities for parsing and formatting references.

This module provides functions for extracting and formatting references from docstrings.
"""

import re
from typing import Any


def parse_references(docstring: str) -> list[dict[str, str]]:
    """Parse references from a docstring.

    Args:
        docstring: Docstring to parse

    Returns:
        list[dict[str, str]]: List of reference dictionaries, each containing:
            - number: Reference number as string
            - text: Reference text
    """
    references = []
    lines = docstring.split("\n")
    in_references = False

    for raw_line in lines:
        line = raw_line.strip()
        if line.lower().startswith("references:"):
            in_references = True
            continue

        if in_references and line:
            # Parse reference line
            match = re.match(r"^\[(\d+)\]\s+(.+)$", line)
            if match:
                number, text = match.groups()
                references.append({"number": number, "text": text})

    return references


def format_references_section(references: list[dict[str, str]]) -> dict[str, Any]:
    """Format references section for documentation.

    Args:
        references: List of reference dictionaries

    Returns:
        dict[str, Any]: Formatted references section containing:
            - title: "References"
            - content: List of reference dictionaries
            - contentType: "references"
    """
    if not references:
        return {}

    return {
        "title": "References",
        "content": references,
        "contentType": "references",
    }
