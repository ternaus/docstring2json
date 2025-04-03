"""Utilities for formatting function and class signatures."""

import inspect
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SignatureData:
    """Data class for function/class signature information."""

    name: str
    params: list[str]
    return_type: str | None = None


def get_signature_params(obj: type | Callable[..., Any]) -> list[str]:
    """Get parameter names from an object's signature.

    Args:
        obj: Class or function to get parameters from

    Returns:
        list[str]: List of parameter names
    """
    try:
        sig = inspect.signature(obj)
        return [
            name
            for name, param in sig.parameters.items()
            if param.kind not in (param.VAR_POSITIONAL, param.VAR_KEYWORD)
        ]
    except ValueError:
        logger.warning("Could not get signature for %s", obj.__name__)
        return []


def format_signature(obj: type | Callable[..., Any], params: list[str] | None = None) -> SignatureData:
    """Format object signature with parameter types.

    Args:
        obj: Class or function to format signature for
        params: Optional list of parameter names

    Returns:
        SignatureData: Formatted signature data
    """
    try:
        sig = inspect.signature(obj)
        if params is None:
            params = get_signature_params(obj)

        # Handle return type annotation
        return_type = None
        if sig.return_annotation != inspect.Parameter.empty:
            if isinstance(sig.return_annotation, inspect.Parameter):
                return_type = sig.return_annotation.name
            else:
                return_type = str(sig.return_annotation)

        return SignatureData(
            name=obj.__name__,
            params=params,
            return_type=return_type,
        )
    except ValueError:
        logger.warning("Could not format signature for %s", obj.__name__)
        return SignatureData(name=obj.__name__, params=[])
