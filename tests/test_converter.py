"""Tests for the docstring_2tsx converter module."""

import inspect
from typing import Any, Callable

import pytest

from docstring_2tsx.converter import class_to_data


class SimpleClass:
    """A simple test class with docstring.

    This is a test class used to test docstring parsing.

    Attributes:
        name: Name of the class instance
        value: Numeric value
    """

    def __init__(self, name: str, value: int = 0):
        """Initialize the class.

        Args:
            name: Name of the class instance
            value: Numeric value
        """
        self.name = name
        self.value = value

    def get_value(self) -> int:
        """Get the value.

        Returns:
            int: The current value
        """
        return self.value


def simple_function(param1: str, param2: int = 42) -> str:
    """A simple test function with docstring.

    This is a test function used to test docstring parsing.

    Args:
        param1: First parameter
        param2: Second parameter with default value

    Returns:
        str: A string combining the parameters

    Examples:
        >>> simple_function("test", 1)
        'test1'
    """
    return f"{param1}{param2}"


class ClassWithoutDocs:
    def __init__(self):
        pass

    def method(self):
        pass


def function_without_docs(param):
    return param


@pytest.mark.parametrize(
    "test_obj,expected_fields",
    [
        (
            SimpleClass,
            {
                "name": "SimpleClass",
                "type": "class",
                "docstring": {"Description": "A simple test class with docstring."},
            },
        ),
        (
            simple_function,
            {
                "name": "simple_function",
                "type": "function",
                "docstring": {"Description": "A simple test function with docstring."},
            },
        ),
        (
            ClassWithoutDocs,
            {
                "name": "ClassWithoutDocs",
                "type": "class",
                "docstring": {},
            },
        ),
        (
            function_without_docs,
            {
                "name": "function_without_docs",
                "type": "function",
                "docstring": {},
            },
        ),
    ],
)
def test_class_to_data_basic_fields(test_obj: Any, expected_fields: dict[str, Any]) -> None:
    """Test that class_to_data returns the expected basic fields."""
    result = class_to_data(test_obj)

    # Check expected fields exist
    for key, value in expected_fields.items():
        assert key in result
        if key == "docstring" and "Description" in value:
            assert "Description" in result[key]
            assert value["Description"] in result[key]["Description"]
        else:
            assert result[key] == value

    # Check all required fields exist
    assert "signature" in result
    assert "source_line" in result


@pytest.mark.parametrize(
    "test_obj,expected_param_count",
    [
        (SimpleClass, 2),  # __init__ has name and value
        (simple_function, 2),  # param1 and param2
        (ClassWithoutDocs, 0),  # No documented params
        (function_without_docs, 1),  # One param but not documented
    ],
)
def test_class_to_data_params(test_obj: Any, expected_param_count: int) -> None:
    """Test that class_to_data correctly captures parameter information."""
    result = class_to_data(test_obj)

    # Check signature params
    assert len(result["signature"]["params"]) == expected_param_count

    # For objects with parameters, test more details
    if expected_param_count > 0 and isinstance(test_obj, Callable):
        sig = inspect.signature(test_obj)
        for param_name in sig.parameters:
            if param_name not in ("self", "cls"):
                # Check param exists in signature
                param_names = [p["name"] for p in result["signature"]["params"]]
                assert param_name in param_names


@pytest.mark.parametrize(
    "test_obj,expected_sections",
    [
        (SimpleClass, ["Attributes"]),
        (simple_function, ["Examples", "Returns"]),
        (ClassWithoutDocs, []),
        (function_without_docs, []),
    ],
)
def test_class_to_data_sections(test_obj: Any, expected_sections: list[str]) -> None:
    """Test that class_to_data correctly extracts docstring sections."""
    result = class_to_data(test_obj)

    # Check that the docstring contains the expected sections
    for section in expected_sections:
        assert section in result["docstring"]


def test_class_to_data_source_code() -> None:
    """Test that class_to_data includes source code when available."""
    result = class_to_data(simple_function)

    # Source code should be included and contain the function definition
    assert "source_code" in result
    assert "def simple_function" in result["source_code"]
    assert "return f\"{param1}{param2}\"" in result["source_code"]
