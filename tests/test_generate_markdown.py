from pathlib import Path
import pytest
import types
import importlib
from typing import Any, Callable

from google_docstring_2md.converter import class_to_markdown, package_to_markdown_structure

# Sample class with Google-style docstring for testing
class SampleClass:
    """Sample class with Google-style docstring.

    This is a longer description of the sample class
    that spans multiple lines to show how formatting works.

    Args:
        param1 (str): The first parameter.
        param2 (int): The second parameter with a longer
            description that spans multiple lines.
        param3 (bool, optional): Optional parameter. Defaults to True.

    Returns:
        dict: A dictionary containing the processed results.

    Example:
        >>> obj = SampleClass("example", 42)
        >>> result = obj.process()
        >>> print(result)
        {'status': 'success', 'value': 42}

    Note:
        This is just a sample class for demonstration purposes.
    """

    def __init__(self, param1, param2, param3=True):
        self.param1 = param1
        self.param2 = param2
        self.param3 = param3

    def process(self):
        """Process the parameters and return a result.

        Returns:
            dict: The processing result.
        """
        return {"status": "success", "value": self.param2}


# Private sample class
class _PrivateSampleClass:
    """A private sample class that should be excluded when exclude_private is True."""

    def __init__(self):
        pass


@pytest.fixture
def output_dir() -> Path:
    """Fixture providing a clean output directory for tests."""
    path = Path("./test_output")
    path.mkdir(exist_ok=True, parents=True)
    return path


@pytest.fixture
def mock_package() -> Any:
    """Fixture providing a mock package for testing."""
    # Create a simple module for testing
    mock_pkg = types.ModuleType("mock_package")
    mock_pkg.SampleClass = SampleClass
    mock_pkg._PrivateSampleClass = _PrivateSampleClass
    mock_pkg.__name__ = "mock_package"

    # Mock a module within the package
    submodule = types.ModuleType("mock_package.submodule")
    submodule.AnotherClass = type("AnotherClass", (), {
        "__doc__": "Another class docstring",
        "__module__": "mock_package.submodule"
    })
    submodule.__name__ = "mock_package.submodule"

    # Connect modules
    mock_pkg.submodule = submodule

    return mock_pkg


@pytest.fixture
def mock_importlib(mock_package: Any) -> None:
    """Fixture that mocks importlib.import_module."""
    original_import = importlib.import_module

    def _import_mock(name: str) -> Any:
        if name == "mock_package":
            return mock_package
        return original_import(name)

    importlib.import_module = _import_mock
    yield
    importlib.import_module = original_import


@pytest.mark.parametrize("test_class,expected_text", [
    (SampleClass, ["# SampleClass", "**Parameters**", "**Returns**", "**Example**", "**Note**"]),
    (_PrivateSampleClass, ["# _PrivateSampleClass"])
])
def test_class_to_markdown(test_class: Any, expected_text: list[str], output_dir: Path) -> None:
    """Test that class_to_markdown generates correct markdown sections."""
    markdown = class_to_markdown(test_class)

    # Check if all expected sections are in the markdown
    for text in expected_text:
        assert text in markdown, f"Expected text '{text}' not found in markdown"

    # Save output for inspection
    output_file = output_dir / f"{test_class.__name__}.md"
    output_file.write_text(markdown)


@pytest.mark.parametrize("exclude_private,should_contain_private", [
    (False, True),
    (True, False)
])
def test_package_structure(exclude_private: bool, should_contain_private: bool,
                           output_dir: Path, mock_package: Any, mock_importlib: Any) -> None:
    """Test that package_to_markdown_structure handles private classes correctly."""
    # Create subfolder for this test
    test_output_dir = output_dir / f"package_test_exclude_{exclude_private}"
    test_output_dir.mkdir(exist_ok=True, parents=True)

    # Generate documentation
    package_to_markdown_structure("mock_package", test_output_dir, exclude_private=exclude_private)

    # Check if private class files were generated according to exclude_private setting
    private_file = test_output_dir / "_PrivateSampleClass.md"

    if should_contain_private:
        assert private_file.exists(), "Private class file should exist when exclude_private=False"
    else:
        assert not private_file.exists(), "Private class file should not exist when exclude_private=True"

    # Check if regular class file was generated in both cases
    regular_file = test_output_dir / "SampleClass.md"
    assert regular_file.exists(), "Regular class file should always exist"

    # Check if submodule was processed
    submodule_dir = test_output_dir / "submodule"
    assert submodule_dir.exists(), "Submodule directory should be created"
    assert (submodule_dir / "AnotherClass.md").exists(), "Submodule class file should exist"
