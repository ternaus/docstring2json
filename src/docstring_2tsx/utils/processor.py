"""Utilities for processing docstrings into TSX components."""

from google_docstring_parser import ParsedGoogleDocstring


def process_description(parsed: ParsedGoogleDocstring) -> str:
    """Process the description section of a docstring.

    Args:
        parsed: Parsed Google docstring

    Returns:
        TSX formatted description
    """
    if not parsed.description:
        return ""
    return f"<p>{parsed.description}</p>"


def build_params_table(params: list[str], parsed: ParsedGoogleDocstring) -> list[str]:
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
    for param in params:
        param_doc = next((p for p in parsed.params if p.name == param), None)
        description = param_doc.description if param_doc else ""
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


def process_other_sections(parsed: ParsedGoogleDocstring) -> list[str]:
    """Process remaining sections of a docstring.

    Args:
        parsed: Parsed Google docstring

    Returns:
        List of TSX formatted sections
    """
    sections = []

    # Add returns section
    if parsed.returns:
        sections.extend(
            [
                "<h2>Returns</h2>",
                f"<p>{parsed.returns.description}</p>",
            ],
        )

    # Add raises section
    if parsed.raises:
        sections.extend(["<h2>Raises</h2>", "<ul>"])
        sections.extend(f"<li><code>{exc.type_name}</code>: {exc.description}</li>" for exc in parsed.raises)
        sections.append("</ul>")

    return sections
