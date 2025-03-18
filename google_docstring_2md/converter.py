"""Utilities for converting Google-style docstrings to Markdown.

This module provides functions to convert Python classes and functions with Google-style
docstrings into Markdown documentation.
"""

import inspect
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from google_docstring_parser import parse_google_docstring

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class Parameter:
    """Parameter information extracted from signature and docstring."""

    name: str
    type: str
    default: Any
    description: str = ""


def get_signature_params(obj: type | Callable) -> list[Parameter]:
    """Extract parameters from object signature.

    Args:
        obj (type | Callable): Class or function to extract parameters from

    Returns:
        List of Parameter objects containing name, type, default value
    """
    signature = inspect.signature(obj)
    params = []

    for name, param in signature.parameters.items():
        # Get parameter type annotation
        if param.annotation is not inspect.Signature.empty:
            if hasattr(param.annotation, "__name__"):
                param_type = param.annotation.__name__
            else:
                param_type = str(param.annotation).replace("typing.", "")
                # Clean up typing annotations (remove typing. prefix)
                if "'" in param_type:
                    param_type = param_type.split("'")[1]
        else:
            param_type = ""

        # Get default value
        default = param.default if param.default is not inspect.Signature.empty else None

        params.append(Parameter(name=name, type=param_type, default=default))

    return params


def format_default_value(value: object) -> str:
    """Format default value for signature display.

    Args:
        value (object): Parameter default value

    Returns:
        Formatted string representation of the value
    """
    if value is None:
        return "None"
    if isinstance(value, str):
        return f"'{value}'"
    return str(value)


def format_section_content(section: str, content: str) -> str:
    """Format section content, handling special cases like code examples.

    Args:
        section (str): Section name (e.g. "Examples", "Notes")
        content (str): Raw section content

    Returns:
        Formatted content with proper markdown
    """
    if section in ["Example", "Examples"] and (">>>" in content or "..." in content):
        lines = []
        for line_content in content.split("\n"):
            line_stripped = line_content.strip()
            if line_stripped.startswith((">>> ", "... ")):
                lines.append(line_stripped[4:])
            elif line_stripped:
                lines.append(line_stripped)
        return "```python\n" + "\n".join(lines) + "\n```"
    return content


def _format_signature(obj: type | Callable, params: list[Parameter]) -> str:
    """Format object signature for documentation.

    Args:
        obj (type | Callable): Class or function object
        params (list[Parameter]): List of parameters

    Returns:
        Formatted signature as string
    """
    # Format signature
    param_str = ", ".join(f"{p.name}={format_default_value(p.default)}" for p in params)
    signature = f"{obj.__name__}({param_str})"

    # Handle return annotation for functions
    if inspect.isfunction(obj) and obj.__annotations__.get("return"):
        return_type = obj.__annotations__["return"]
        signature += f" -> {return_type.__name__ if hasattr(return_type, '__name__') else str(return_type)}"

    return signature


def _process_description(parsed: dict) -> str:
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
    return f"{desc}\n"


def _extract_param_docs(param: Parameter, param_docs: dict, obj: type | Callable) -> tuple[str, str]:
    """Extract parameter documentation info.

    Args:
        param (Parameter): Parameter object
        param_docs (dict): Dictionary mapping parameter names to docstring info
        obj (type | Callable): Class or function object

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
        desc = desc.replace("\n", " ")

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

    return doc_type, desc


def _build_params_table(params: list[Parameter], parsed: dict, obj: type | Callable) -> list[str]:
    """Build parameters table from parameter information.

    Args:
        params (list[Parameter]): List of parameter objects
        parsed (dict): Parsed docstring dictionary
        obj (type | Callable): Class or function object

    Returns:
        List of markdown strings for parameter table
    """
    if not parsed.get("Args"):
        return []

    result = [
        "\n## Parameters\n",
        "| Name | Type | Description |\n",
        "|------|------|-------------|\n",
    ]

    # Create a dictionary to lookup parameter info from docstring
    param_docs = {arg["name"]: arg for arg in parsed["Args"]}

    for param in params:
        doc_type, desc = _extract_param_docs(param, param_docs, obj)
        result.append(f"| {param.name} | {doc_type} | {desc} |\n")

    return result


def _process_other_sections(parsed: dict) -> list[str]:
    """Process sections other than Description and Args.

    Args:
        parsed (dict): Parsed docstring dictionary

    Returns:
        List of markdown strings for the other sections
    """
    result = []

    for section, section_content in parsed.items():
        if section not in ["Description", "Args"]:
            if not isinstance(section_content, str):
                if isinstance(section_content, list) and not section_content:
                    continue
                processed_content = str(section_content)
            else:
                processed_content = section_content

            result.extend(
                [
                    f"\n## {section}\n",
                    format_section_content(section, processed_content),
                    "\n",
                ],
            )

    return result


def class_to_markdown(obj: type | Callable) -> str:
    """Convert class or function to markdown documentation.

    This function generates markdown documentation for a class or function,
    extracting information from its docstring and signature.

    Args:
        obj (type | Callable): Class or function to document

    Returns:
        Markdown formatted documentation string
    """
    sections = []

    # Get object name and parameters
    obj_name = obj.__name__
    params = get_signature_params(obj)

    # Format and add the signature
    signature = _format_signature(obj, params)
    sections.extend(
        [
            f"# {obj_name}\n",
            f"```python\n{signature}\n```\n",
        ],
    )

    # Parse docstring
    docstring = obj.__doc__ or ""
    parsed = parse_google_docstring(docstring)

    # Add description
    description = _process_description(parsed)
    if description:
        sections.append(description)

    # Add parameters table
    param_table = _build_params_table(params, parsed, obj)
    sections.extend(param_table)

    # Add remaining sections
    other_sections = _process_other_sections(parsed)
    sections.extend(other_sections)

    return "".join(sections)


def generate_markdown_files(package: object, output_dir: Path) -> None:
    """Generate markdown files for all classes in a package.

    Args:
        package (object): Python package or module
        output_dir (Path): Directory to write markdown files
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, obj in inspect.getmembers(package):
        if inspect.isclass(obj) and obj.__module__.startswith(package.__name__):
            markdown = class_to_markdown(obj)
            output_file = output_dir / f"{name}.md"
            output_file.write_text(markdown)


def module_to_markdown_files(
    module: object,
    output_dir: Path,
    *,
    exclude_private: bool = False,
) -> None:
    """Generate markdown files for all classes and functions in a module.

    Args:
        module (object): Python module
        output_dir (Path): Directory to write markdown files
        exclude_private (bool): Whether to exclude private classes and methods (starting with _)
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process classes and functions
    for name, obj in inspect.getmembers(module):
        # Skip private members if exclude_private is True
        if exclude_private and name.startswith("_"):
            continue

        # Only consider classes and functions defined in this module
        # or directly assigned to this module
        is_in_module = (hasattr(obj, "__module__") and obj.__module__ == module.__name__) or (
            inspect.isclass(obj) or inspect.isfunction(obj)
        )

        if is_in_module:
            try:
                markdown = class_to_markdown(obj)
                output_file = output_dir / f"{name}.md"
                output_file.write_text(markdown)
            except (ValueError, TypeError, AttributeError):
                logger.exception("Error processing %s", name)


def package_to_markdown_structure(
    package_name: str,
    output_dir: Path,
    *,
    exclude_private: bool = False,
) -> None:
    """Convert installed package to markdown files with directory structure.

    Args:
        package_name (str): Name of installed package
        output_dir (Path): Root directory for output markdown files
        exclude_private (bool): Whether to exclude private classes and methods (starting with _)
    """
    import importlib

    try:
        package = importlib.import_module(package_name)
        output_dir.mkdir(exist_ok=True, parents=True)

        # Process the root module directly
        module_to_markdown_files(package, output_dir, exclude_private=exclude_private)

        # Process submodules in the package
        for _name, obj in inspect.getmembers(package):
            if inspect.ismodule(obj) and obj.__name__.startswith(package_name + "."):
                # Create subdirectory for submodule
                rel_name = obj.__name__[len(package_name) + 1 :]
                sub_dir = output_dir / rel_name
                module_to_markdown_files(obj, sub_dir, exclude_private=exclude_private)
    except ImportError:
        logger.exception("Could not import package '%s'", package_name)
    except (ValueError, TypeError, AttributeError):
        logger.exception("Error processing package '%s'", package_name)
