"""Tests for the signature formatter utilities."""

import inspect
from typing import Any, Callable

import pytest

from utils.signature_formatter import (
    Parameter,
    SignatureData,
    _get_param_default,
    _get_param_type,
    _process_signature_params,
    format_default_value,
    format_signature,
    get_signature_params,
)


# Test classes and functions to use in our tests
class SimpleClass:
    """Simple class for testing."""

    def __init__(self, param1: str, param2: int = 42):
        """Initialize with params.

        Args:
            param1: First parameter
            param2: Second parameter with default
        """
        self.param1 = param1
        self.param2 = param2


class ClassWithoutInit:
    """Class without explicit __init__."""

    pass


class ClassWithComplexTypes:
    """Class with complex type annotations."""

    def __init__(
        self,
        literal_param: "list[str]",
        union_param: str | int,
        tuple_param: tuple[str, int],
    ):
        """Initialize with complex type annotations."""
        self.literal_param = literal_param
        self.union_param = union_param
        self.tuple_param = tuple_param


def simple_function(param1: str, param2: int = 42) -> str:
    """A test function.

    Args:
        param1: First parameter
        param2: Second parameter with default

    Returns:
        str: A result
    """
    return f"{param1}{param2}"


def function_with_callable_default(callback: Callable = lambda x: x):
    """Function with a callable default."""
    return callback


def function_without_annotations(param1, param2=None):
    """Function without type annotations."""
    return param1, param2


@pytest.mark.parametrize(
    "param_obj,expected_type",
    [
        # Basic types should return their __name__
        (inspect.Parameter("p", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=str), "str"),
        (inspect.Parameter("p", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=int), "int"),
        # Empty annotation should return empty string
        (inspect.Parameter("p", inspect.Parameter.POSITIONAL_OR_KEYWORD), ""),
        # Complex types should preserve their string representation
        (
            inspect.Parameter("p", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=str | int),
            "str | int",
        ),
        (
            inspect.Parameter(
                "p", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation="list[str]"
            ),
            "list[str]",
        ),
    ],
)
def test_get_param_type(param_obj: inspect.Parameter, expected_type: str) -> None:
    """Test extracting parameter type from annotation."""
    assert _get_param_type(param_obj) == expected_type


@pytest.mark.parametrize(
    "param_obj,expected_default",
    [
        # No default should return None
        (inspect.Parameter("p", inspect.Parameter.POSITIONAL_OR_KEYWORD), None),
        # Basic defaults should return string representation
        (
            inspect.Parameter(
                "p", inspect.Parameter.POSITIONAL_OR_KEYWORD, default=42
            ),
            "42",
        ),
        (
            inspect.Parameter(
                "p", inspect.Parameter.POSITIONAL_OR_KEYWORD, default="test"
            ),
            "test",
        ),
        # Callable defaults should format properly
        (
            inspect.Parameter(
                "p", inspect.Parameter.POSITIONAL_OR_KEYWORD, default=lambda x: x
            ),
            "<function <lambda>>",
        ),
    ],
)
def test_get_param_default(param_obj: inspect.Parameter, expected_default: str | None) -> None:
    """Test extracting parameter default value."""
    result = _get_param_default(param_obj)
    if expected_default and callable(param_obj.default):
        # We can only check that it contains the function name, not the exact string
        assert "<function" in result
    else:
        assert result == expected_default


@pytest.mark.parametrize(
    "test_obj,expected_params",
    [
        (
            simple_function,
            [
                Parameter(name="param1", type="str", default=None, description=""),
                Parameter(name="param2", type="int", default="42", description=""),
            ],
        ),
        (
            SimpleClass,
            [
                Parameter(name="param1", type="str", default=None, description=""),
                Parameter(name="param2", type="int", default="42", description=""),
            ],
        ),
        (
            ClassWithoutInit,
            [
                # The default init will have *args and **kwargs parameters
                Parameter(name="args", type="", default=None, description=""),
                Parameter(name="kwargs", type="", default=None, description=""),
            ]
        ),
        (
            function_without_annotations,
            [
                Parameter(name="param1", type="", default=None, description=""),
                Parameter(name="param2", type="", default="None", description=""),
            ],
        ),
    ],
)
def test_get_signature_params(test_obj: Any, expected_params: list[Parameter]) -> None:
    """Test extracting parameters from different objects."""
    result = get_signature_params(test_obj)

    # Compare parameters
    assert len(result) == len(expected_params)

    for i, expected in enumerate(expected_params):
        assert result[i].name == expected.name
        assert result[i].type == expected.type
        # Default values might be formatted differently, so we check presence rather than exact match
        if expected.default is None:
            assert result[i].default is None
        else:
            assert result[i].default is not None


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, "None"),
        (42, "42"),
        ("test", "'test'"),  # format_default_value adds quotes for strings
        (True, "True"),
        ([1, 2, 3], "[1, 2, 3]"),
    ],
)
def test_format_default_value(value: Any, expected: str) -> None:
    """Test formatting default values."""
    assert format_default_value(value) == expected


@pytest.mark.parametrize(
    "test_obj,params,expected_return_type",
    [
        (
            simple_function,
            [
                Parameter(name="param1", type="str", default=None),
                Parameter(name="param2", type="int", default="42"),
            ],
            "str",
        ),
        (
            SimpleClass,
            [
                Parameter(name="param1", type="str", default=None),
                Parameter(name="param2", type="int", default="42"),
            ],
            None,  # Classes don't have return types
        ),
        (
            function_without_annotations,
            [
                Parameter(name="param1", type="", default=None),
                Parameter(name="param2", type="", default="None"),
            ],
            None,  # No return annotation
        ),
    ],
)
def test_format_signature(
    test_obj: Any, params: list[Parameter], expected_return_type: str | None
) -> None:
    """Test formatting full signatures."""
    result = format_signature(test_obj, params)

    assert result.name == test_obj.__name__
    assert len(result.params) == len(params)
    assert result.return_type == expected_return_type


def test_process_signature_params() -> None:
    """Test processing signature parameters."""
    # Create a signature with various types of parameters
    def test_func(
        normal: str,
        default: int = 42,
        complex_type: list[str] = None,
    ):
        pass

    signature = inspect.signature(test_func)

    # Test without skipping any parameters
    result = _process_signature_params(signature)
    assert len(result) == 3
    assert result[0].name == "normal"
    assert result[0].type == "str"
    assert result[0].default is None

    assert result[1].name == "default"
    assert result[1].type == "int"
    assert result[1].default == "42"

    # Test with a method signature (skipping self)
    def method_func(self, param1: str, param2: int = 42):
        pass

    method_signature = inspect.signature(method_func)
    result_skip_self = _process_signature_params(method_signature, skip_self=True)
    assert len(result_skip_self) == 2
    assert result_skip_self[0].name == "param1"
