"""Tests for the TSX converter module."""

import json
from typing import Any

import pytest
from typing import Any, Mapping, Sequence

from src.docstring_2tsx.processor import (
    process_description,
    build_params_data,
    format_section_data,
    _format_raises_data,
    _format_returns_data,
)
from src.docstring_2tsx.converter import class_to_data, COMPONENTS_IMPORT_PATH
from src.utils.signature_formatter import Parameter, SignatureData


class DummyClass:
    """This is a dummy class for testing.

    This class is used to test the TSX converter functionality.
    It has a simple docstring with various sections.

    Args:
        param1 (str): The first parameter
        param2 (int): The second parameter with a default value

    Returns:
        None: This class doesn't return anything

    Example:
        >>> dummy = DummyClass("test", 42)
        >>> dummy.method()
    """

    def __init__(self, param1: str, param2: int = 42):
        """Initialize the DummyClass.

        Args:
            param1: The first parameter
            param2: The second parameter with default value
        """
        self.param1 = param1
        self.param2 = param2

    def method(self) -> str:
        """A test method.

        Returns:
            str: A test string
        """
        return "test"


def dummy_function(param1: str, param2: int = 42) -> str:
    """A dummy function for testing.

    Args:
        param1: The first parameter
        param2: The second parameter with default value

    Returns:
        str: A test string

    Raises:
        ValueError: If param1 is empty

    Example:
        >>> result = dummy_function("test", 42)
        >>> print(result)
        test
    """
    if not param1:
        raise ValueError("param1 cannot be empty")
    return param1


def test_process_description_empty() -> None:
    """Test processing empty description."""
    parsed: dict[str, str | list[Any] | dict[str, Any]] = {"Description": ""}
    assert process_description(parsed) is None


def test_process_description_with_content() -> None:
    """Test processing description with content."""
    parsed: dict[str, str | list[Any] | dict[str, Any]] = {"Description": "Test description"}
    assert process_description(parsed) == "Test description"


def test_build_params_data() -> None:
    """Test building parameters data structure."""
    params = [
        Parameter(name="param1", type="str", default=None),
        Parameter(name="param2", type="int", default="42"),
    ]
    parsed = {
        "Args": [
            {"name": "param1", "type": "str", "description": "First parameter"},
            {"name": "param2", "type": "int", "description": "Second parameter"},
        ],
    }

    result = build_params_data(params, parsed)
    assert result is not None
    assert len(result) == 2
    assert result[0]["name"] == "param1"
    assert result[0]["type"] == "str"
    assert result[0]["description"] == "First parameter"
    assert result[1]["name"] == "param2"
    assert result[1]["type"] == "int"
    assert result[1]["description"] == "Second parameter"


def test_format_returns_data() -> None:
    """Test formatting returns data."""
    content = {
        "type": "str",
        "description": "Return value description",
    }
    result = _format_returns_data(content)
    assert result == {
        "type": "str",
        "description": "Return value description",
    }


def test_format_raises_data() -> None:
    """Test formatting raises data."""
    content: list[dict[str, str]] = [
        {
            "type": "ValueError",
            "description": "When value is invalid",
        },
        {
            "type": "TypeError",
            "description": "When type is wrong",
        },
    ]
    result = _format_raises_data(content)
    assert result == [
        {
            "type": "ValueError",
            "description": "When value is invalid",
        },
        {
            "type": "TypeError",
            "description": "When type is wrong",
        },
    ]


def test_format_section_data() -> None:
    """Test formatting section data."""
    section = "Example"
    content = "Example code here"
    result = format_section_data(section, content)
    assert result == {
        "title": "Example",
        "content": content,
        "contentType": "code",
    }


def test_format_section_data_with_returns() -> None:
    """Test formatting section data with returns."""
    section = "Returns"
    content = {"type": "str", "description": "Return value"}
    result = format_section_data(section, content)
    assert result == {
        "title": "Returns",
        "content": {"type": "str", "description": "Return value"},
        "contentType": "data",
    }


def test_format_section_data_with_raises() -> None:
    """Test formatting section data with raises."""
    section = "Raises"
    content = [{"type": "ValueError", "description": "Invalid value"}]
    result = format_section_data(section, content)
    assert result == {
        "title": "Raises",
        "content": [{"type": "ValueError", "description": "Invalid value"}],
        "contentType": "data",
    }


def test_format_section_data_with_empty_content() -> None:
    """Test formatting section data with empty content."""
    section = "Notes"
    content = ""
    result = format_section_data(section, content)
    assert result is None


def test_class_to_data():
    """Test the class_to_data function."""
    # Test with a class
    result = class_to_data(DummyClass)

    # Check basic structure
    assert isinstance(result, dict)
    assert result["name"] == "DummyClass"
    assert result["type"] == "class"

    # Check signature
    signature = result["signature"]
    assert signature["name"] == "DummyClass"
    assert len(signature["params"]) == 2
    assert signature["params"][0]["name"] == "param1"
    assert signature["params"][0]["type"] == "str"
    assert signature["params"][1]["name"] == "param2"
    assert signature["params"][1]["type"] == "int"
    assert signature["params"][1]["default"] == "42"

    # Check docstring
    docstring = result["docstring"]
    assert isinstance(docstring, dict)
    assert "Description" in docstring
    assert "Args" in docstring
    assert "Returns" in docstring
    assert "Example" in docstring

    # Test with a function
    result = class_to_data(dummy_function)

    # Check basic structure
    assert isinstance(result, dict)
    assert result["name"] == "dummy_function"
    assert result["type"] == "function"

    # Check signature
    signature = result["signature"]
    assert signature["name"] == "dummy_function"
    assert len(signature["params"]) == 2
    assert signature["params"][0]["name"] == "param1"
    assert signature["params"][0]["type"] == "str"
    assert signature["params"][1]["name"] == "param2"
    assert signature["params"][1]["type"] == "int"
    assert signature["params"][1]["default"] == "42"
    assert signature["return_type"] == "str"

    # Check docstring
    docstring = result["docstring"]
    assert isinstance(docstring, dict)
    assert "Description" in docstring
    assert "Args" in docstring
    assert "Returns" in docstring
    assert "Raises" in docstring
    assert "Example" in docstring


def test_tsx_content_generation(monkeypatch):
    """Test TSX content generation."""
    from src.docstring_2tsx.converter import file_to_tsx

    class MockModule:
        """Mock module for testing."""

        __doc__ = "Module docstring"
        __name__ = "test_module"

    def mock_collect_module_members(*args, **kwargs):
        return [("DummyClass", DummyClass)], [("dummy_function", dummy_function)]

    def mock_class_to_data(*args, **kwargs):
        return {
            "name": "test",
            "type": "class",
            "signature": {
                "name": "test",
                "params": [],
                "return_type": None,
            },
            "docstring": {"Description": "Test description"},
        }

    monkeypatch.setattr(
        "src.docstring_2tsx.converter.collect_module_members",
        mock_collect_module_members,
    )
    monkeypatch.setattr("src.docstring_2tsx.converter.class_to_data", mock_class_to_data)

    result = file_to_tsx(MockModule, "test_module")

    # Check basic structure
    assert isinstance(result, str)
    assert result.startswith(f"import {{ ModuleDoc }} from '{COMPONENTS_IMPORT_PATH}'")
    assert "export default function Page()" in result

    # Parse the moduleData JSON
    start = result.find("const moduleData = ") + len("const moduleData = ")
    end = result.find(";\n\nexport")
    module_data = json.loads(result[start:end])

    # Check module data structure
    assert isinstance(module_data, dict)
    assert module_data["moduleName"] == "test_module"
    assert "docstring" in module_data
    assert "members" in module_data
    assert isinstance(module_data["members"], list)
    assert len(module_data["members"]) == 2  # One for class, one for function
