"""Tests for the docstring_2tsx converter module."""

import inspect
from typing import Any, Callable
import json
from unittest.mock import patch

import pytest

from docstring_2tsx.converter import class_to_data, serialize_module_data, process_member


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


def test_serialize_module_data_handles_normal_data():
    """Test that serialize_module_data can handle normal JSON-serializable data."""
    # Simple data that should serialize without issues
    test_data = {
        "moduleName": "test_module",
        "docstring": "Test docstring",
        "members": [{"name": "test_member", "type": "function"}],
    }

    result = serialize_module_data(test_data, "test_module")
    parsed_result = json.loads(result)

    # Check that the result is valid JSON and contains the expected data
    assert parsed_result["moduleName"] == "test_module"
    assert parsed_result["docstring"] == "Test docstring"
    assert len(parsed_result["members"]) == 1
    assert parsed_result["members"][0]["name"] == "test_member"


def test_serialize_module_data_handles_unserializable_data():
    """Test that serialize_module_data can handle unserializable data."""
    # Create an object that can't be serialized to JSON
    class UnserializableObject:
        def __repr__(self):
            return "Unserializable"

    test_data = {
        "moduleName": "test_module",
        "docstring": "Test docstring",
        "members": [{"obj": UnserializableObject()}],
    }

    # This should fall back to a simplified version
    result = serialize_module_data(test_data, "test_module")

    # Since we know the simplified version is valid JSON, we can parse it
    try:
        parsed_result = json.loads(result)
        assert parsed_result["moduleName"] == "test_module"
        assert parsed_result["docstring"] == "Error serializing module data"
        assert parsed_result["members"] == []
    except json.JSONDecodeError:
        # If we get here, it's using the ultimate fallback which is a JS literal
        assert "moduleName: 'test_module'" in result
        assert "docstring: 'Error serializing module data'" in result
        assert "members: []" in result


def test_process_member_handles_normal_class():
    """Test that process_member can handle a normal class."""
    result = process_member(SimpleClass)

    assert result is not None
    assert result["name"] == "SimpleClass"
    assert result["type"] == "class"
    assert "signature" in result
    assert "docstring" in result


def test_process_member_handles_errors():
    """Test that process_member returns None when processing fails."""
    # Create a mock that raises an exception when processed
    class ProblemClass:
        __name__ = "ProblemClass"

        def __signature__(self):
            raise ValueError("Test error")

    # Mock class_to_data to raise an exception
    def mock_class_to_data(obj):
        raise ValueError("Test error")

    # Use patch to temporarily replace class_to_data
    with patch("docstring_2tsx.converter.class_to_data", side_effect=mock_class_to_data):
        result = process_member(ProblemClass)
        assert result is None
