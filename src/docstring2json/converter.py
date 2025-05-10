"""Utilities for converting Google-style docstrings to TSX.

This module provides functions to convert Python classes and functions with Google-style
docstrings into TSX documentation components that use imported React components.
"""

import inspect
import json
import logging
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any, TypeVar, cast

# Add the project root directory to sys.path
src_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(src_dir))

# Add the src directory itself to sys.path
parent_dir = Path(__file__).parent.parent  # This is the src directory
sys.path.insert(0, str(parent_dir))

from google_docstring_parser import parse_google_docstring

from docstring2json.utils.signature_formatter import format_signature, get_signature_params

# Configure logging
logger = logging.getLogger(__name__)

# Define type aliases for the imported functions
SignatureFormatterType = Callable[[type | Callable[..., Any], list[Any]], Any]
GetSignatureParamsType = Callable[[type | Callable[..., Any]], list[Any]]

# Error messages
ERR_EXPECTED_DICT = "Expected dict result from convert_to_serializable"


# Type definitions
T = TypeVar("T")
JSONSerializable = str | int | float | bool | None | dict[str, "JSONSerializable"] | list["JSONSerializable"]
ComplexObject = JSONSerializable | object | Mapping[str | object, Any] | Sequence[Any]


def collect_module_members(module: ModuleType) -> tuple[list[tuple[str, type]], list[tuple[str, Callable[..., Any]]]]:
    """Collect classes and functions from a module.

    Args:
        module: The module to collect members from

    Returns:
        tuple[list[tuple[str, type]], list[tuple[str, Callable[..., Any]]]]:
            Tuple of (classes, functions) where each is a list of (name, obj) pairs
    """
    classes: list[tuple[str, type]] = []
    functions: list[tuple[str, Callable[..., Any]]] = []

    for name, obj in inspect.getmembers(module):
        # Skip private members and imported objects
        if name.startswith("_") or inspect.getmodule(obj) != inspect.getmodule(module):
            continue

        if inspect.isclass(obj):
            classes.append((name, obj))
        elif inspect.isfunction(obj):
            functions.append((name, obj))

    return classes, functions


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

    return data.__name__ if isinstance(data, type) else str(data)


def get_class_ancestors(cls: type) -> list[str]:
    """Get the list of ancestor class names for a given class.

    Args:
        cls: The class to get ancestors for

    Returns:
        list[str]: List of ancestor class names, excluding 'object'
    """
    # Get all base classes in Method Resolution Order (MRO), excluding 'object'
    return [base.__name__ for base in cls.__mro__[1:] if base.__name__ != "object"]


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
    # Get source code only
    source_code = get_source_code(obj)

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
            "params": signature_params,
        },
        "docstring": parsed,
    }

    # Add return_type only for functions
    if not isinstance(obj, type):
        member_data["signature"]["return_type"] = (
            signature_data.return_type.__name__
            if signature_data.return_type is not None and hasattr(signature_data.return_type, "__name__")
            else str(signature_data.return_type)
            if signature_data.return_type is not None
            else None
        )
    # Add ancestors list only for classes
    else:
        member_data["ancestors"] = get_class_ancestors(obj)

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


def file_to_json(module: ModuleType, module_name: str) -> str:
    """Convert a module to a JSON document with just the data.

    Args:
        module: The module object to document
        module_name: Name of the module for the heading

    Returns:
        str: The JSON content
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
    module_data["members"] = cast("Any", members_data)

    # Sanitize data and convert to JSON
    sanitized_data = sanitize_for_json(module_data)
    return serialize_module_data(sanitized_data, module_name)
