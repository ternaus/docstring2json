"""Tests for the TSX converter module."""

import json
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

    assert result["name"] == "DummyClass"
    assert result["type"] == "class"
    assert "signature" in result
    assert isinstance(result["signature"], dict)
    assert result["signature"]["name"] == "DummyClass"
    assert "params" in result["signature"]
    assert "description" in result
    assert "params" in result
    assert len(result["params"]) == 2

    # Test with a function
    result = class_to_data(dummy_function)

    assert result["name"] == "dummy_function"
    assert result["type"] == "function"
    assert "signature" in result
    assert isinstance(result["signature"], dict)
    assert result["signature"]["name"] == "dummy_function"
    assert "params" in result["signature"]
    assert result["signature"]["return_type"] == "str"
    assert "description" in result
    assert "params" in result
    assert "sections" in result
    assert any(section["title"] == "Returns" for section in result["sections"])
    assert any(section["title"] == "Raises" for section in result["sections"])
    assert any(section["title"] == "Example" for section in result["sections"])


def test_tsx_content_generation(monkeypatch):
    """Test the generation of TSX content with a mocked module."""
    # Mock data generation for a cleaner test
    mock_data = {
        "name": "TestModule",
        "members": [
            {
                "name": "TestClass",
                "type": "class",
                "signature": {
                    "name": "TestClass",
                    "params": [
                        {"name": "param1", "type": "str", "default": None, "description": "First parameter"},
                        {"name": "param2", "type": "int", "default": 42, "description": "Second parameter"}
                    ],
                    "return_type": None
                },
                "description": "This is a test class",
                "params": [
                    {"name": "param1", "type": "str", "description": "First parameter"},
                    {"name": "param2", "type": "int", "description": "Second parameter"},
                ],
            }
        ],
    }

    # Import here to avoid circular import issues in the test
    from src.docstring_2tsx.converter import file_to_tsx

    # Mock class_to_data to return our test data
    def mock_class_to_data(*args, **kwargs):
        return mock_data["members"][0]

    monkeypatch.setattr("src.docstring_2tsx.converter.class_to_data", mock_class_to_data)
    monkeypatch.setattr("src.docstring_2tsx.converter.collect_module_members", lambda x: ([], [("test", DummyClass)]))

    # Test the file_to_tsx function
    result = file_to_tsx(None, "test_module")

    # Check that the result contains what we expect
    assert f"import {{ ModuleDoc" in result
    assert f"}} from '{COMPONENTS_IMPORT_PATH}';" in result
    assert "const moduleData =" in result
    assert "export default function Page()" in result
    assert "return <ModuleDoc {...moduleData} />;" in result

    # Parse the JSON data from the generated file
    json_str = result.split("const moduleData =")[1].split(";\n\nexport")[0].strip()
    data = json.loads(json_str)

    # Verify the data structure
    assert data["moduleName"] == "test_module"
    assert len(data["members"]) == 1
    assert data["members"][0]["name"] == "TestClass"
    assert data["members"][0]["type"] == "class"
    assert len(data["members"][0]["params"]) == 2
