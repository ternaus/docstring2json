"""Utilities for converting Google-style docstrings to TSX.

This module provides functions to convert Python classes and functions with Google-style
docstrings into TSX documentation components that use imported React components.
"""

import inspect
import json
import logging
from collections.abc import Callable, Mapping, Sequence
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

# Type definitions
T = TypeVar("T")
JSONSerializable = str | int | float | bool | None | dict[str, "JSONSerializable"] | list["JSONSerializable"]
ComplexObject = JSONSerializable | object | Mapping[str | object, Any] | Sequence[Any]

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


def sanitize_for_json(data: ComplexObject) -> JSONSerializable:
    """Convert complex Python objects to JSON-compatible types.

    Args:
        data: Data to convert to JSON-serializable format

    Returns:
        JSONSerializable: JSON-compatible data
    """
    if isinstance(data, (str, int, float, bool, type(None))):
        return data
    if isinstance(data, dict):
        return {str(k): sanitize_for_json(v) for k, v in data.items()}
    if isinstance(data, (list, tuple)):
        return [sanitize_for_json(item) for item in data]
    if isinstance(data, type):
        # For type objects, return just the name
        return data.__name__
    # Convert anything else to string
    return str(data)


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

    # Try to extract parameter information, but handle cases where signature isn't available
    signature_params = []
    try:
        if not isinstance(obj, type) or hasattr(obj, "__init__"):
            sig = inspect.signature(obj)
            signature_params = [
                {
                    "name": param.name,
                    "type": param.annotation.__name__
                    if param.annotation != inspect.Parameter.empty and hasattr(param.annotation, "__name__")
                    else str(param.annotation)
                    if param.annotation != inspect.Parameter.empty
                    else "Any",
                    "default": str(param.default) if param.default != inspect.Parameter.empty else None,
                }
                for param in sig.parameters.values()
                if param.kind not in (param.VAR_POSITIONAL, param.VAR_KEYWORD)
            ]
    except (ValueError, TypeError):
        logger.warning("Could not extract signature for %s", obj_name)

    # Create the data structure
    member_data: dict[str, Any] = {
        "name": obj_name,
        "type": "class" if isinstance(obj, type) else "function",
        "signature": {
            "name": signature_data.name,
            "params": signature_params,
            "return_type": signature_data.return_type.__name__
            if hasattr(signature_data.return_type, "__name__")
            else str(signature_data.return_type)
            if signature_data.return_type
            else None,
        },
        "docstring": parsed,
        "source_line": source_line,
    }

    # Add source code if available
    if source_code:
        member_data["source_code"] = source_code

    return member_data


def serialize_module_data(data: ComplexObject, module_name: str) -> str:
    """Serialize module data to JSON with fallback handling.

    Args:
        data: The module data to serialize
        module_name: The name of the module for fallback data

    Returns:
        str: JSON string representation of the data
    """
    try:
        return json.dumps(data, indent=2)
    except TypeError:
        logger.exception("Error serializing data to JSON, data may contain non-serializable types")
        fallback_data = {
            "moduleName": module_name,
            "docstring": "Error serializing module data",
            "members": [],
        }
        try:
            return json.dumps(fallback_data, indent=2)
        except TypeError:
            # Ultimate fallback - handle even if the mock json.dumps always raises an error
            return f"{{ moduleName: '{module_name}', docstring: 'Error serializing module data', members: [] }}"


def process_member(obj: type | Callable[..., Any]) -> dict[str, Any] | None:
    """Process a class or function member to extract documentation.

    Args:
        obj: The class or function to process

    Returns:
        dict[str, Any] | None: The processed member data or None if processing failed
    """
    try:
        return class_to_data(obj)
    except Exception:
        logger.exception("Failed to process member %s", obj.__name__)
        return None


def file_to_tsx(module: ModuleType, module_name: str) -> str:
    """Convert a module to a TSX document that uses imported components.

    Args:
        module: The module object to document
        module_name: Name of the module for the heading

    Returns:
        str: The TSX content
    """
    # Create basic module data structure with raw docstring
    module_data = {
        "moduleName": module_name,
        "docstring": module.__doc__ or "",
        "members": [],
    }

    # Collect module members
    classes, functions = collect_module_members(module)
    members_data: list[dict[str, Any]] = []

    # Process classes and functions using the helper
    for _name, class_obj in classes:
        member_data = process_member(class_obj)
        if member_data:
            members_data.append(member_data)

    for _name, func_obj in functions:
        member_data = process_member(func_obj)
        if member_data:
            members_data.append(member_data)

    # Add members to module data
    module_data["members"] = members_data  # type: ignore[assignment]

    # Sanitize data and convert to JSON using the helper
    sanitized_data = sanitize_for_json(module_data)
    module_data_str = serialize_module_data(sanitized_data, module_name)

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
