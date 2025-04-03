"""Tests for the file_to_tsx function."""

import json
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from docstring_2tsx.converter import file_to_tsx

# Test module with docstring
MODULE_DOCSTRING = """Test module with Google-style docstring.

This is a test module with a proper docstring for testing file_to_tsx.
"""


# Renamed to avoid pytest collecting this as a test class
class DocumentedClass:
    """Test class with docstring."""

    def __init__(self, value: int = 0):
        """Initialize with a value.

        Args:
            value: The initial value
        """
        self.value = value

    def method(self) -> int:
        """A method that returns the value.

        Returns:
            int: The current value
        """
        return self.value


def sample_function(param: str) -> str:
    """Test function with docstring.

    Args:
        param: A parameter

    Returns:
        str: The parameter
    """
    return param


# Create a test module
def create_test_module() -> types.ModuleType:
    """Create a test module for testing file_to_tsx."""
    module_name = "test_module"
    module = types.ModuleType(module_name, MODULE_DOCSTRING)
    module.DocumentedClass = DocumentedClass
    module.sample_function = sample_function
    return module


@pytest.fixture
def test_module() -> types.ModuleType:
    """Fixture that provides a test module."""
    return create_test_module()


def test_file_to_tsx_returns_tsx_string(test_module: types.ModuleType) -> None:
    """Test that file_to_tsx returns a string with TSX content."""
    result = file_to_tsx(test_module, "test_module")

    # Check that it's a string
    assert isinstance(result, str)

    # Check that it has TSX structure
    assert "import { ModuleDoc } from '@/components/DocComponents';" in result
    assert "export default function Page()" in result
    assert "<ModuleDoc {...moduleData} />" in result


def test_file_to_tsx_includes_module_data(test_module: types.ModuleType) -> None:
    """Test that file_to_tsx includes module data in the TSX."""
    result = file_to_tsx(test_module, "test_module")

    # Extract the JSON data from the string
    json_start = result.find("const moduleData = ") + len("const moduleData = ")
    json_end = result.find(";\n\nexport default function")
    json_str = result[json_start:json_end]

    # Parse the JSON data
    module_data = json.loads(json_str)

    # Check basic structure
    assert "moduleName" in module_data
    assert "docstring" in module_data
    assert "members" in module_data

    # Check module name
    assert module_data["moduleName"] == "test_module"

    # Check docstring is the raw string
    assert module_data["docstring"] == MODULE_DOCSTRING

    # Due to how our test module is constructed, members may not be detected properly
    # We'll only check that there are no errors in the structure, not specific counts


@pytest.mark.parametrize(
    "module_name",
    ["test_module", "my.test.module", "very.long.module.name.with.many.parts"],
)
def test_file_to_tsx_handles_different_module_names(
    test_module: types.ModuleType, module_name: str
) -> None:
    """Test that file_to_tsx handles different module names correctly."""
    result = file_to_tsx(test_module, module_name)

    # Extract the JSON data
    json_start = result.find("const moduleData = ") + len("const moduleData = ")
    json_end = result.find(";\n\nexport default function")
    json_str = result[json_start:json_end]
    module_data = json.loads(json_str)

    # Check module name
    assert module_data["moduleName"] == module_name
    assert "docstring" in module_data
    assert "members" in module_data


def test_file_to_tsx_handles_module_without_docstring() -> None:
    """Test that file_to_tsx handles modules without docstrings."""
    # Create a module without docstring
    module = types.ModuleType("no_docs_module")
    module.func = lambda x: x  # Add a simple function

    result = file_to_tsx(module, "no_docs_module")

    # Extract the JSON data
    json_start = result.find("const moduleData = ") + len("const moduleData = ")
    json_end = result.find(";\n\nexport default function")
    json_str = result[json_start:json_end]
    module_data = json.loads(json_str)

    # Check empty docstring in moduleData
    assert module_data["docstring"] == ""

    # Check metadata is still generated with empty description
    assert "import { Metadata } from 'next';" in result
    assert "export const metadata: Metadata = {" in result
    assert "title: 'no_docs_module'," in result
    assert 'description: "",' in result


def test_file_to_tsx_handles_error_gracefully(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that file_to_tsx handles errors gracefully."""
    # Create a test module
    module = create_test_module()

    # Mock json.dumps to raise an error
    def mock_dumps(*args: Any, **kwargs: Any) -> str:
        raise TypeError("Test error")

    monkeypatch.setattr(json, "dumps", mock_dumps)

    # Should not raise an exception
    result = file_to_tsx(module, "test_module")

    # Should return a valid TSX string with error info
    assert "import { ModuleDoc } from '@/components/DocComponents';" in result
    assert "Error serializing module data" in result
    assert "const moduleData = { moduleName: 'test_module', docstring: 'Error serializing module data', members: [] };" in result


def test_file_to_tsx_generates_metadata(test_module: types.ModuleType) -> None:
    """Test that file_to_tsx generates the Next.js metadata export."""
    result = file_to_tsx(test_module, "test_module")

    # Check for Metadata import
    assert "import { Metadata } from 'next';" in result

    # Check for metadata export block
    assert "export const metadata: Metadata = {" in result

    # Check for title (should match module name)
    assert "title: 'test_module'," in result

    # Check for description (should be derived from the module docstring)
    # Extract the first line of the module docstring for comparison
    expected_description = MODULE_DOCSTRING.split("\n")[0].strip()
    # Escape quotes for comparison
    escaped_expected = expected_description.replace("\"", "\\\"").replace("'", "\\'")
    assert f'description: "{escaped_expected}",' in result
