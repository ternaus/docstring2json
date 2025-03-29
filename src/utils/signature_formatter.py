"""Utilities for formatting function and class signatures.

This module provides functions for extracting and formatting function and class signatures,
including parameter formatting and documentation.
"""

import inspect
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .config import MAX_SIGNATURE_LINE_LENGTH

logger = logging.getLogger(__name__)


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
        obj (Union[type, Callable]): Class or function to extract parameters from

    Returns:
        List of Parameter objects containing name, type, default value
    """
    try:
        signature = inspect.signature(obj)
        params = []

        for name, param in signature.parameters.items():
            # Get parameter type annotation
            if param.annotation is inspect.Signature.empty:
                param_type = ""
            elif hasattr(param.annotation, "__name__"):
                param_type = param.annotation.__name__
            else:
                param_type = str(param.annotation).replace("typing.", "")
                # Clean up typing annotations (remove typing. prefix)
                if "'" in param_type:
                    param_type = param_type.split("'")[1]
                # For Literal types, keep the full type string
                if param_type.startswith("Literal"):
                    param_type = str(param.annotation)

            # Get default value
            default = param.default if param.default is not inspect.Signature.empty else None

            params.append(Parameter(name=name, type=param_type, default=default))
    except (ValueError, TypeError):
        # Handle built-in types, Exception classes, or other types without a signature
        logger.debug("Could not get signature for %s, returning empty parameters list", obj.__name__)
        return []
    else:
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
    return f"'{value}'" if isinstance(value, str) else str(value)


def _format_long_signature(obj_name: str, param_parts: list[str]) -> str:
    """Format a long function signature with line breaks and indentation.

    Args:
        obj_name (str): Name of the object (function/class)
        param_parts (list[str]): List of formatted parameter strings

    Returns:
        str: Formatted signature with line breaks
    """
    # Indent parameters to align with the opening parenthesis
    indent_size = len(obj_name) + 1  # Function name + opening parenthesis
    indentation = " " * indent_size

    # Start with the function name and opening parenthesis
    signature_lines = [f"{obj_name}("]

    # Add parameters with indentation
    for i, param in enumerate(param_parts):
        # Add comma if not the last parameter
        suffix = "," if i < len(param_parts) - 1 else ""
        signature_lines.append(f"{indentation}{param}{suffix}")

    # Close the parenthesis
    signature_lines.append(")")

    # Join the lines with newlines
    return "\n".join(signature_lines)


def format_signature(obj: type | Callable, params: list[Parameter]) -> str:
    """Format object signature for documentation.

    Args:
        obj (Union[type, Callable]): Class or function object
        params (list[Parameter]): List of parameters

    Returns:
        Formatted signature as string
    """
    # If no parameters, return a simple signature
    if not params:
        signature = f"{obj.__name__}()"
    else:
        # Format each parameter
        param_parts = [f"{p.name}={format_default_value(p.default)}" for p in params]

        # Check if the signature would be too long
        full_line = f"{obj.__name__}({', '.join(param_parts)})"

        # If the signature is short enough, use a single line
        if len(full_line) <= MAX_SIGNATURE_LINE_LENGTH:
            signature = full_line
        else:
            # For long signatures, format with line breaks and indentation
            signature = _format_long_signature(obj.__name__, param_parts)

    # Handle return annotation for functions
    if inspect.isfunction(obj) and obj.__annotations__.get("return"):
        return_type = obj.__annotations__["return"]
        ret_type_str = return_type.__name__ if hasattr(return_type, "__name__") else str(return_type)
        signature += f" -> {ret_type_str}"

    return signature
