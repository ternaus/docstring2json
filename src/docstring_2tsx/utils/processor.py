"""Utilities for processing docstrings into TSX components."""

from typing import Any


def process_description(parsed: dict[str, Any]) -> str:
    """Process the description section of a docstring.

    Args:
        parsed: Parsed Google docstring

    Returns:
        TSX formatted description
    """
    if not parsed.get("description"):
        return ""
    return f"<p>{parsed['description']}</p>"


def build_params_table(params: list[str], parsed: dict[str, Any]) -> list[str]:
    """Build a table of parameters in TSX format.

    Args:
        params: List of parameter names
        parsed: Parsed Google docstring

    Returns:
        List of TSX table rows
    """
    if not params:
        return []

    sections = [
        "<h2>Parameters</h2>",
        "<table>",
        "<thead>",
        "<tr>",
        "<th>Name</th>",
        "<th>Description</th>",
        "</tr>",
        "</thead>",
        "<tbody>",
    ]

    # Add each parameter
    parsed_params = parsed.get("params", [])
    for param in params:
        param_doc = next((p for p in parsed_params if p["name"] == param), None)
        description = param_doc["description"] if param_doc else ""
        sections.extend(
            [
                "<tr>",
                f"<td><code>{param}</code></td>",
                f"<td>{description}</td>",
                "</tr>",
            ],
        )

    sections.extend(["</tbody>", "</table>"])
    return sections


def process_other_sections(parsed: dict[str, Any]) -> list[str]:
    """Process remaining sections of a docstring.

    Args:
        parsed: Parsed Google docstring

    Returns:
        List of TSX formatted sections
    """
    sections = []

    # Add returns section
    if returns := parsed.get("returns"):
        sections.extend(
            [
                "<h2>Returns</h2>",
                f"<p>{returns['description']}</p>",
            ],
        )

    # Add raises section
    if raises := parsed.get("raises", []):
        sections.extend(["<h2>Raises</h2>", "<ul>"])
        sections.extend(f"<li><code>{exc['type_name']}</code>: {exc['description']}</li>" for exc in raises)
        sections.append("</ul>")

    return sections
