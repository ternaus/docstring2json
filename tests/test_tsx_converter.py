"""Tests for the TSX converter module."""

import json
import pytest

from src.docstring_2tsx.processor import (
    process_description,
    build_params_data,
    format_section_data,
)
from src.docstring_2tsx.converter import class_to_data, COMPONENTS_IMPORT_PATH
from src.utils.signature_formatter import Parameter


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


def test_process_description():
    """Test the process_description function."""
    # Test with a valid description
    parsed = {"Description": "This is a test description"}
    result = process_description(parsed)
    assert result == "This is a test description"

    # Test with no description
    parsed = {}
    result = process_description(parsed)
    assert result is None


def test_build_params_data():
    """Test the build_params_data function."""
    # Create some parameters
    params = [
        Parameter(name="param1", type="str", default=None, description=""),
        Parameter(name="param2", type="int", default=42, description=""),
    ]

    # Create parsed docstring data
    parsed = {
        "Args": [
            {"name": "param1", "type": "str", "description": "The first parameter"},
            {"name": "param2", "type": "int", "description": "The second parameter with default value"},
        ]
    }

    # Test with valid parameters and docstring
    result = build_params_data(params, parsed)
    assert len(result) == 2
    assert result[0]["name"] == "param1"
    assert result[0]["type"] == "str"
    assert result[0]["description"] == "The first parameter"
    assert result[1]["name"] == "param2"
    assert result[1]["type"] == "int"
    assert result[1]["description"] == "The second parameter with default value"

    # Test with no parameters
    result = build_params_data([], parsed)
    assert result is None


def test_format_section_data():
    """Test the format_section_data function."""
    # Test with Returns section
    result = format_section_data("Returns", "str: A test string")
    assert result is not None
    assert result["title"] == "Returns"
    assert result["contentType"] == "data"

    # Test with Example section
    result = format_section_data("Example", ">>> result = test()\n>>> print(result)")
    assert result is not None
    assert result["title"] == "Example"
    assert result["contentType"] == "code"
    assert ">>> result = test()" in result["content"]

    # Test with References section
    result = format_section_data("References", "Author: Book Title")
    assert result is not None
    assert result["title"] == "References"
    assert result["contentType"] == "reference"
    assert len(result["content"]) == 1
    assert result["content"][0]["description"] == "Author"
    assert result["content"][0]["source"] == "Book Title"

    # Test with empty content
    result = format_section_data("Notes", "")
    assert result is None


def test_class_to_data():
    """Test the class_to_data function."""
    # Test with a class
    result = class_to_data(DummyClass, github_repo="https://github.com/user/repo")

    assert result["name"] == "DummyClass"
    assert result["type"] == "class"
    assert "signature" in result
    assert "description" in result
    assert "params" in result
    assert len(result["params"]) == 2
    assert result["githubUrl"].startswith("https://github.com/user/repo/blob/main/")

    # Test with a function
    result = class_to_data(dummy_function, github_repo="https://github.com/user/repo")

    assert result["name"] == "dummy_function"
    assert result["type"] == "function"
    assert "signature" in result
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
                "signature": "TestClass(param1: str, param2: int = 42)",
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
    assert f"import {{ ModuleDoc, MemberDoc" in result
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
