"""Utilities for parsing references in Google-style docstrings.

This module provides functions to parse and format Reference/References sections
from docstrings into structured data.
"""

import re
from collections.abc import Callable
from re import Match


def _parse_single_reference(content: str) -> dict[str, str]:
    """Parse a single reference from content.

    Args:
        content (str): Content containing a single reference

    Returns:
        dict[str, str]: Dictionary with 'description' and 'source' keys
    """
    if ":" in content:
        colon_idx = content.find(":")
        description = content[:colon_idx].strip()
        source = content[colon_idx + 1 :].strip()
        return {"description": description, "source": source}
    # No colon separator found, treat as description only
    return {"description": content, "source": ""}


def _process_reference_line(
    line: str,
    current_ref: dict[str, str] | None,
    current_indent: int,
) -> tuple[dict[str, str] | None, int]:
    """Process a line for a reference with dash.

    Args:
        line (str): Line of text to process
        current_ref (Optional[dict[str, str]]): The current reference being built, if any
        current_indent (int): Current indentation level

    Returns:
        tuple[Optional[dict[str, str]], int]: Tuple of (possibly updated reference, new indent level)
    """
    stripped = line.lstrip()
    line_indent = len(line) - len(stripped)

    if not stripped.startswith("-"):
        return current_ref, current_indent

    # Remove dash and find colon separator
    content = stripped[1:].strip()
    return _parse_single_reference(content), line_indent


def _process_continuation_line(line: str, current_ref: dict[str, str]) -> dict[str, str]:
    """Process a continuation line for a reference.

    Args:
        line (str): Line of text to process
        current_ref (dict[str, str]): The current reference being built

    Returns:
        dict[str, str]: Updated reference dictionary
    """
    stripped = line.lstrip()
    if ":" in stripped and not current_ref["source"]:
        # This might be the source part
        colon_idx = stripped.find(":")
        desc_part = stripped[:colon_idx].strip()
        source_part = stripped[colon_idx + 1 :].strip()

        # Append to description and set source
        current_ref["description"] = f"{current_ref['description']} {desc_part}"
        current_ref["source"] = source_part
    # Continuation of description or source
    elif current_ref["source"]:
        current_ref["source"] = f"{current_ref['source']} {stripped}"
    else:
        current_ref["description"] = f"{current_ref['description']} {stripped}"

    return current_ref


def parse_references(reference_content: str) -> list[dict[str, str]]:
    """Parse references section into structured format.

    Args:
        reference_content (str): The content of the References section

    Returns:
        list[dict[str, str]]: A list of dictionaries with 'description' and 'source' keys
    """
    references = []
    lines = [line for line in reference_content.strip().split("\n") if line.strip()]

    # Handle empty reference content
    if not lines:
        return references

    # Check if we have multiple references (indicated by dash prefixes)
    has_dashes = any(line.lstrip().startswith("-") for line in lines)

    if has_dashes:
        # Process multiple references with dashes
        current_ref = None
        current_indent = 0

        for line in lines:
            stripped = line.lstrip()
            line_indent = len(line) - len(stripped)

            if stripped.startswith("-"):
                # New reference
                if current_ref:
                    references.append(current_ref)

                # Process the line as a new reference
                current_ref, current_indent = _process_reference_line(line, current_ref, current_indent)
            elif current_ref and line_indent > current_indent:
                # Process continuation of previous reference
                current_ref = _process_continuation_line(line, current_ref)

        # Add the last reference
        if current_ref:
            references.append(current_ref)
    else:
        # Single reference
        content = "\n".join(lines)
        references.append(_parse_single_reference(content))

    return references


def format_url(text: str) -> str:
    """Format a text string, converting URLs to markdown links.

    Args:
        text (str): Text that might contain URLs

    Returns:
        str: Text with URLs converted to markdown links
    """
    # Regex for URL pattern
    url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+\.[^\s<>"]{2,}'

    # Function to convert URL to markdown link
    def replace_with_link(match: Match[str]) -> str:
        url = match.group(0)
        # If URL starts with www, add https://
        if url.startswith("www."):
            url = f"https://{url}"
        # Return markdown link
        return f"[{url}]({url})"

    # Replace URLs with markdown links
    return re.sub(url_pattern, replace_with_link, text)


def format_references(
    references: list[dict[str, str]],
    escape_func: Callable[[str], str] | None = None,
) -> str:
    """Format references as markdown.

    Args:
        references (list[dict[str, str]]): List of reference dictionaries with 'description' and 'source' keys
        escape_func (Callable[[str], str], optional): Function to escape special characters in the text

    Returns:
        str: Formatted markdown for references
    """
    if not references:
        return ""

    # Apply escaping function if provided
    def process_text(text: str) -> str:
        if escape_func and callable(escape_func):
            text = escape_func(text)
        return format_url(text)

    # Format as a list if multiple references, or a paragraph if single reference
    if len(references) > 1:
        formatted_refs = []
        for ref in references:
            desc = process_text(ref["description"])
            source = process_text(ref["source"])
            formatted_refs.append(f"- **{desc}**: {source}")
        return "\n".join(formatted_refs)
    # Single reference
    ref = references[0]
    desc = process_text(ref["description"])
    source = process_text(ref["source"])
    return f"**{desc}**: {source}"
