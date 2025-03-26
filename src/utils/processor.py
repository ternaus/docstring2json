"""Utilities for processing Google-style docstrings.

This module provides functions for parsing and formatting different sections of
Google-style docstrings into Markdown format.
"""

import re
from collections.abc import Callable

from .reference_parser import format_references, parse_references
from .signature_formatter import Parameter


def escape_mdx_special_chars(text: str) -> str:
    """Escape special characters that might cause issues in MDX files.

    Args:
        text (str): Text to escape

    Returns:
        str: Escaped text safe for MDX files
    """
    if not text:
        return text

    # Escape characters that might cause parsing issues in MDX
    escaped = text.replace("<", "\\<").replace(">", "\\>").replace("=", "\\=")

    # Replace multiple backslashes (e.g. \\n) with a code format
    # This is to avoid issues with LaTeX-like code that uses backslashes
    escaped = re.sub(r"\\{2,}", lambda m: f"`{m.group(0)}`", escaped)

    # Escape curly braces, which are special in MDX/JSX
    return escaped.replace("{", "\\{").replace("}", "\\}")


def is_example_section(section: str, content: str) -> bool:
    """Check if section is an example section with code examples.

    Args:
        section (str): Section name
        content (str): Section content

    Returns:
        bool: True if section is an example section with code examples
    """
    examples_sections = {"Example", "Examples"}
    return section in examples_sections and (">>>" in content or "..." in content)


def is_reference_section(section: str) -> bool:
    """Check if section is a references section.

    Args:
        section (str): Section name

    Returns:
        bool: True if section is a references section
    """
    references_sections = {"References", "Reference"}
    return section in references_sections


def format_examples(content: str) -> str:
    """Format example code blocks.

    Args:
        content (str): Raw example content with interpreter prompts

    Returns:
        str: Formatted Python code block
    """
    lines = []
    for line_content in content.split("\n"):
        line_stripped = line_content.strip()
        if line_stripped.startswith((">>> ", "... ")):
            lines.append(line_stripped[4:])
        elif line_stripped:
            lines.append(line_stripped)
    return "```python\n" + "\n".join(lines) + "\n```"


def format_references_section(content: str) -> str:
    """Format references section.

    Args:
        content (str): Raw references content

    Returns:
        str: Formatted references in Markdown
    """
    references = parse_references(content)
    return format_references(references, escape_func=escape_mdx_special_chars)


def wrap_in_code_block(content: str) -> str:
    """Wrap content in a code block.

    Args:
        content (str): Raw content

    Returns:
        str: Content wrapped in code block
    """
    return "```\n" + content + "\n```"


def format_section_content(section: str, content: str) -> str:
    """Format section content, handling special cases like code examples.

    Args:
        section (str): Section name (e.g. "Examples", "Notes")
        content (str): Raw section content

    Returns:
        Formatted content with proper markdown
    """
    if is_example_section(section, content):
        return format_examples(content)

    if is_reference_section(section):
        return format_references_section(content)

    # Use code blocks instead of PreserveFormat
    return wrap_in_code_block(content)


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
    desc = escape_mdx_special_chars(desc)

    return f"{desc}\n"


def extract_param_docs(param: Parameter, param_docs: dict, obj: type | Callable) -> tuple[str, str]:
    """Extract parameter documentation info.

    Args:
        param (Parameter): Parameter object
        param_docs (dict): Dictionary mapping parameter names to docstring info
        obj (Union[type, Callable]): Class or function object

    Returns:
        Tuple of (type, description)
    """
    # Get parameter description from docstring or use empty string
    desc = ""
    param_name = param.name

    # If our parameter is in the docstring, use that info
    if param_name in param_docs:
        desc = param_docs[param_name].get("description", "")
        if not isinstance(desc, str):
            desc = str(desc)

        # Get type from docstring if available
        doc_type = param_docs[param_name].get("type", "")
    else:
        # If parameter not found in docstring, use type from signature
        doc_type = param.type

    # If no type could be found, check annotations
    if not doc_type and param_name in obj.__annotations__:
        annotation = obj.__annotations__[param_name]
        if hasattr(annotation, "__name__"):
            doc_type = annotation.__name__
        else:
            doc_type = str(annotation).replace("typing.", "")
            if "'" in doc_type:
                doc_type = doc_type.split("'")[1]

    if not isinstance(doc_type, str):
        doc_type = str(doc_type)

    # Escape special characters for type
    doc_type = escape_mdx_special_chars(doc_type)

    return doc_type, desc


def build_params_table(params: list[Parameter], parsed: dict, obj: type | Callable) -> list[str]:
    """Build a parameters table from the docstring and signature.

    Args:
        params (list): List of parameter objects from signature
        parsed (dict): Parsed docstring dictionary
        obj (Union[type, Callable]): Class or function object

    Returns:
        List of markdown strings for the parameters table
    """
    # Skip parameters table if no parameters
    if not params or all(param.name in {"self", "cls"} for param in params):
        return []

    # Use standard markdown table
    result = [
        "\n**Parameters**\n",
        "| Name | Type | Description |\n",
        "|------|------|-------------|\n",
    ]

    # Create a dictionary to lookup parameter info from docstring
    param_docs = {}
    if "Args" in parsed:
        param_docs = {arg["name"]: arg for arg in parsed["Args"]}

    for param in params:
        doc_type, desc = extract_param_docs(param, param_docs, obj)

        # Escape the parameter name
        param_name = escape_mdx_special_chars(param.name)

        # Handle description formatting
        if desc:
            # First escape special characters in the description
            safe_desc = escape_mdx_special_chars(desc)

            # For multi-line content, we'll replace escaped newlines with actual HTML tags
            # This way the HTML tags won't get escaped by _escape_mdx_special_chars
            if "\n" in desc:
                # Replace newlines with unescaped HTML line breaks
                # We need to make sure we don't escape the HTML tags
                html_breaks = safe_desc.replace("\n", "<br/>")
                # Now make an unescaped pre tag wrapper
                safe_desc = f"<pre>{html_breaks}</pre>"

                # Replace the escaped < and > in our HTML tags with actual < and >
                safe_desc = safe_desc.replace("\\<br/\\>", "<br/>")
                safe_desc = safe_desc.replace("\\<pre\\>", "<pre>")
                safe_desc = safe_desc.replace("\\</pre\\>", "</pre>")
        else:
            safe_desc = ""

        result.append(f"| {param_name} | {doc_type} | {safe_desc} |\n")

    return result


def process_other_sections(parsed: dict) -> list[str]:
    """Process sections other than Description and Args.

    Args:
        parsed (dict): Parsed docstring dictionary

    Returns:
        List of markdown strings for the other sections
    """
    result = []

    for section, section_content in parsed.items():
        if section not in ["Description", "Args"]:
            # Skip empty lists
            if isinstance(section_content, list) and not section_content:
                continue

            processed_content = section_content if isinstance(section_content, str) else str(section_content)

            result.extend(
                [
                    f"\n**{section}**\n",
                    format_section_content(section, processed_content),
                    "\n",
                ],
            )

    return result
