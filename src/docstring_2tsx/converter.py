"""Utilities for converting Google-style docstrings to TSX.

This module provides functions to convert Python classes and functions with Google-style
docstrings into TSX documentation components that use imported React components.
"""

import inspect
import json
import logging
from collections.abc import Callable
from types import ModuleType
from typing import Any, TypeVar

from google_docstring_parser import parse_google_docstring

from utils.signature_formatter import (
    format_signature,
    get_signature_params,
)

logger = logging.getLogger(__name__)

# Path to import components from, could be made configurable
COMPONENTS_IMPORT_PATH = "@/components/DocComponents"

# Error messages
ERR_EXPECTED_DICT = "Expected dict result from convert_to_serializable"

T = TypeVar("T")

# Type aliases to make signatures more readable
ClassTuple = tuple[str, type]
FunctionTuple = tuple[str, Callable[..., Any]]
ClassOrFunction = type | Callable[..., Any]


def collect_module_members(module: ModuleType) -> tuple[list[ClassTuple], list[FunctionTuple]]:
    """Collect classes and functions from a module.

    Args:
        module: The module to collect members from

    Returns:
        tuple[list[ClassTuple], list[FunctionTuple]]:
            Tuple of (classes, functions) where each is a list of (name, obj) pairs
    """
    classes: list[ClassTuple] = []
    functions: list[FunctionTuple] = []

    for name, obj in inspect.getmembers(module):
        # Skip private members and imported objects
        if name.startswith("_") or inspect.getmodule(obj) != inspect.getmodule(module):
            continue

        if inspect.isclass(obj):
            classes.append((name, obj))
        elif inspect.isfunction(obj):
            functions.append((name, obj))

    return classes, functions


def get_source_line(obj: type | Callable[..., Any]) -> int:
    """Get the source line number for a class or function.

    Args:
        obj: Class or function to get source line for

    Returns:
        int: Line number in the source file
    """
    try:
        return obj.__code__.co_firstlineno if hasattr(obj, "__code__") else 1
    except AttributeError:
        return 1


def get_source_code(obj: type | Callable[..., Any]) -> str | None:
    """Get source code for a class or function.

    Args:
        obj: Class or function to get source code for

    Returns:
        str | None: Source code as string or None if not available
    """
    try:
        import inspect

        return inspect.getsource(obj)
    except (TypeError, OSError):
        return None


def convert_to_serializable(
    obj: str | float | bool | None | dict[str, Any] | list[Any],
) -> str | int | float | bool | None | dict[str, Any] | list[Any]:
    """Convert objects to JSON serializable format.

    Args:
        obj: Object to convert

    Returns:
        str | int | float | bool | None | dict[str, Any] | list[Any]: JSON serializable object
    """
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    if isinstance(obj, dict):
        return {str(k): convert_to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    return str(obj)


def class_to_data(obj: type | Callable[..., Any]) -> dict[str, Any]:
    """Convert class or function to structured data format.

    This function extracts documentation data for a class or function from
    its docstring and signature, returning a structured dictionary.

    Args:
        obj: Class or function to document

    Returns:
        dict[str, Any]: Dictionary containing structured documentation data
    """
    # Get object name and parameters
    obj_name = obj.__name__
    params = get_signature_params(obj)
    # Get signature data
    signature_data = format_signature(obj, params)
    # Get source code and line number
    source_code = get_source_code(obj)
    source_line = get_source_line(obj)

    # Parse docstring
    docstring = obj.__doc__ or ""
    try:
        parsed = parse_google_docstring(docstring)
    except Exception:
        logger.exception("Error parsing docstring for %s", docstring)
        parsed = {}

    # Create the data structure
    member_data: dict[str, Any] = {
        "name": obj_name,
        "type": "class" if isinstance(obj, type) else "function",
        "signature": {
            "name": signature_data.name,
            "params": [
                {
                    "name": param.name,
                    "type": param.annotation if param.annotation != inspect.Parameter.empty else "Any",
                    "default": param.default if param.default != inspect.Parameter.empty else None,
                    "description": parsed.get("params", {}).get(param.name, ""),
                }
                for param in inspect.signature(obj).parameters.values()
                if param.kind not in (param.VAR_POSITIONAL, param.VAR_KEYWORD)
            ],
            "return_type": signature_data.return_type,
        },
        "description": parsed.get("description", ""),
        "params": [
            {
                "name": name,
                "type": param_type,
                "description": description,
            }
            for name, (param_type, description) in parsed.get("params", {}).items()
        ],
        "sections": [
            {
                "title": section.title,
                "content": section.content,
                "contentType": "text",
            }
            for section in parsed.get("sections", [])
        ],
        "source_line": source_line,
    }

    # Add source code if available
    if source_code:
        member_data["source_code"] = source_code

    return member_data


def file_to_tsx(module: ModuleType, module_name: str) -> str:
    """Convert a module to a TSX document that uses imported components.

    Args:
        module: The module object to document
        module_name: Name of the module for the heading

    Returns:
        str: The TSX content
    """
    # Collect module members
    classes, functions = collect_module_members(module)

    # Process classes and functions to get their data
    members_data: list[dict[str, Any]] = []

    # Process all classes first, then all functions
    for _name, class_obj in classes:
        member_data = class_to_data(class_obj)
        members_data.append(member_data)

    for _name, func_obj in functions:
        member_data = class_to_data(func_obj)
        members_data.append(member_data)

    # Parse module-level docstring
    module_docstring = module.__doc__ or ""
    try:
        parsed = parse_google_docstring(module_docstring)
        module_data = {
            "moduleName": module_name,
            "description": parsed.get("description", ""),
            "members": members_data,
        }
    except Exception:
        logger.exception("Error parsing module docstring for %s", module_name)
        module_data = {
            "moduleName": module_name,
            "description": "",
            "members": members_data,
        }

    # JSON representation of the data (with indentation for readability)
    module_data_str = json.dumps(module_data, indent=2)

    # Create the page.tsx file content
    components = "ModuleDoc"
    return (
        f"import {{ {components} }} from '{COMPONENTS_IMPORT_PATH}';\n\n"
        "// Data structure extracted from Python docstrings\n"
        f"const moduleData = {module_data_str};\n\n"
        "export default function Page() {\n"
        "  return <ModuleDoc {...moduleData} />;\n"
        "}\n"
    )
