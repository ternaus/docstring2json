"""Utilities for formatting function and class signatures.

This module provides functions for extracting and formatting function and class signatures,
including parameter formatting and documentation.
"""

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class Parameter:
    """Parameter information extracted from signature and docstring."""

    name: str
    type: str
    default: Any
    description: str = ""


@dataclass
class SignatureData:
    """Structured signature data for frontend rendering."""

    name: str
    params: list[Parameter]
    return_type: str | None = None


def _get_param_type(param: inspect.Parameter) -> str:
    """Extract and format parameter type annotation.

    Args:
        param: Parameter object from inspect.signature

    Returns:
        str: Formatted type string, with typing. prefix removed and special handling
            for Literal, Union, and tuple types
    """
    if param.annotation is inspect.Signature.empty:
        return ""

    if hasattr(param.annotation, "__name__"):
        return param.annotation.__name__

    # For complex types like Literal, Union, etc., keep the full type string
    param_type = str(param.annotation)
    # Clean up typing annotations (remove typing. prefix)
    param_type = param_type.replace("typing.", "")
    # For Literal types, keep the full type string
    if param_type.startswith("Literal"):
        return str(param.annotation)
    # For union types (using |), keep the full type string
    if "|" in param_type:
        return str(param.annotation)
    # For tuple types, keep the full type string
    if param_type.startswith("tuple"):
        return str(param.annotation)

    return param_type


def _get_param_default(param: inspect.Parameter) -> str | None:
    """Get parameter default value.

    Args:
        param: Parameter object from inspect.signature

    Returns:
        str | None: Default value formatted as string, or None if no default value exists.
            For callable defaults, returns '<function name>'
    """
    if param.default is inspect.Signature.empty:
        return None

    # Handle function defaults
    if callable(param.default):
        return f"<function {param.default.__name__}>"

    return str(param.default)


def _process_signature_params(signature: inspect.Signature, *, skip_self: bool = False) -> list[Parameter]:
    """Process parameters from a signature.

    Args:
        signature: Function or method signature
        skip_self: Whether to skip 'self' parameter for methods

    Returns:
        list[Parameter]: List of Parameter objects containing name, type, and default value
            for each parameter in the signature
    """
    params = []
    for name, param in signature.parameters.items():
        if skip_self and name == "self":
            continue

        param_type = _get_param_type(param)
        default = _get_param_default(param)
        params.append(Parameter(name=name, type=param_type, default=default))

    return params


def get_signature_params(obj: type | Callable[..., Any]) -> list[Parameter]:
    """Extract parameters from object signature.

    Args:
        obj: Class or function to extract parameters from

    Returns:
        list[Parameter]: List of Parameter objects containing name, type, and default value
            for each parameter in the object's signature. Returns empty list for built-in types
            or objects without signatures
    """
    try:
        if isinstance(obj, type):
            # For classes, try to get __init__ signature
            # Skip if it's an __init__.py file (module)
            if obj.__name__ == "__init__":
                return []

            try:
                # Get __init__ method from the class
                init_method = inspect.getattr_static(obj, "__init__")
                if not callable(init_method):
                    return []
                signature = inspect.signature(init_method)
                return _process_signature_params(signature, skip_self=True)
            except (ValueError, TypeError):
                # If __init__ is not found or has no signature, return empty list
                return []
        else:
            # For functions, get signature directly
            signature = inspect.signature(obj)
            return _process_signature_params(signature)
    except (ValueError, TypeError):
        # Handle built-in types, Exception classes, or other types without a signature
        return []


def format_default_value(value: object) -> str:
    """Format default value for signature display.

    Args:
        value: Parameter default value

    Returns:
        str: Formatted string representation of the value, with special handling for
            None and string values
    """
    if value is None:
        return "None"
    return f"'{value}'" if isinstance(value, str) else str(value)


def format_signature(obj: type | Callable[..., Any], params: list[Parameter]) -> SignatureData:
    """Format object signature for documentation.

    Args:
        obj: Class or function object
        params: List of parameters

    Returns:
        SignatureData: Object containing structured signature information including name,
            parameters, and return type (for functions)
    """
    # Get return type for functions
    return_type = None
    if inspect.isfunction(obj) and obj.__annotations__.get("return"):
        return_type = obj.__annotations__["return"]
        return_type = return_type.__name__ if hasattr(return_type, "__name__") else str(return_type)

    return SignatureData(
        name=obj.__name__,
        params=params,
        return_type=return_type,
    )
