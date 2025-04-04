"""Tests for the TSX converter module."""

import json

import pytest

from src.docstring2tsx.converter import class_to_data


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
    from src.docstring2tsx.converter import file_to_tsx, COMPONENTS_IMPORT_PATH

    class MockModule:
        """Mock module for testing."""

        __doc__ = "Module docstring"
        __name__ = "test_module"

    def mock_collect_module_members(*args, **kwargs):
        # Return dummy data matching expected structure
        dummy_class = type('DummyClass', (), {'__doc__': 'Dummy class doc', '__name__': 'DummyClass'})
        dummy_function = lambda x: x
        dummy_function.__name__ = 'dummy_function'
        dummy_function.__doc__ = 'Dummy function doc'
        return [("DummyClass", dummy_class)], [("dummy_function", dummy_function)]

    def mock_class_to_data(*args, **kwargs):
        # Ensure mock returns required fields, including ancestors for classes
        obj = args[0]
        obj_type = "class" if isinstance(obj, type) else "function"
        data = {
            "name": obj.__name__,
            "type": obj_type,
            "signature": {
                "name": obj.__name__,
                "params": [],
            },
            "docstring": {"Description": obj.__doc__},
            "source_line": 1, # Mock value
        }
        if obj_type == "class":
            data["ancestors"] = [] # Mock value
        else:
             data["signature"]["return_type"] = None # Mock value
        return data

    monkeypatch.setattr(
        "src.docstring2tsx.converter.collect_module_members",
        mock_collect_module_members,
    )
    monkeypatch.setattr("src.docstring2tsx.converter.class_to_data", mock_class_to_data)

    result = file_to_tsx(MockModule, "test_module")

    # Check basic structure
    assert isinstance(result, str)
    assert result.startswith(f"import {{ ModuleDoc }} from '{COMPONENTS_IMPORT_PATH}'")
    assert "import { Metadata } from 'next';" in result # Check metadata import
    assert "export const metadata: Metadata = {" in result # Check metadata export
    assert "export default function Page()" in result

    # Parse the moduleData JSON - find it after the metadata block
    # Find the start of the moduleData definition
    json_start_marker = "const moduleData = "
    json_start_pos = result.find(json_start_marker)
    assert json_start_pos != -1, "Could not find 'const moduleData = ' marker"

    # Find the end of the moduleData definition (before the Page export)
    json_end_marker = ";\n\nexport default function Page()"
    json_end_pos = result.find(json_end_marker, json_start_pos)
    assert json_end_pos != -1, "Could not find end marker ';\n\nexport default function Page()'"

    # Extract the JSON string
    json_str = result[json_start_pos + len(json_start_marker) : json_end_pos]

    # Parse the JSON data
    try:
        module_data = json.loads(json_str)
    except json.JSONDecodeError as e:
        pytest.fail(f"Failed to parse JSON: {e}\nJSON string was: {json_str}")

    # Check module data structure
    assert isinstance(module_data, dict)
    assert module_data["moduleName"] == "test_module"
    assert "docstring" in module_data
    assert module_data["docstring"] == "Module docstring"
    assert "members" in module_data
    assert isinstance(module_data["members"], list)
    assert len(module_data["members"]) == 2  # One for class, one for function
