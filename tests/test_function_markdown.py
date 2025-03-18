import pytest
from pathlib import Path

from google_docstring_2md.converter import class_to_markdown


def sample_function(param1: str, param2: int = 42, param3: bool = True) -> dict:
    """Sample function with Google-style docstring.

    This function demonstrates how to use Google-style docstrings in functions.

    Args:
        param1: The first parameter description.
        param2: The second parameter with default value.
        param3: Boolean parameter.

    Returns:
        A dictionary containing the processed results.

    Example:
        >>> result = sample_function("example")
        >>> print(result)
        {'param1': 'example', 'param2': 42, 'param3': True}
    """
    return {"param1": param1, "param2": param2, "param3": param3}


def private_function(internal_param: str) -> str:
    """A private function that should be excluded when exclude_private is True."""
    return f"processed: {internal_param}"


@pytest.fixture
def output_dir() -> Path:
    """Fixture providing a clean output directory for tests."""
    path = Path("./test_output/functions")
    path.mkdir(exist_ok=True, parents=True)
    return path


@pytest.mark.parametrize("test_func,expected_text", [
    (sample_function, ["# sample_function", "**Parameters**", "**Returns**", "**Example**"]),
    (private_function, ["# private_function", "A private function"])
])
def test_function_to_markdown(test_func, expected_text: list[str], output_dir: Path) -> None:
    """Test that class_to_markdown can also handle functions correctly."""
    markdown = class_to_markdown(test_func)

    # Check if all expected sections are in the markdown
    for text in expected_text:
        assert text in markdown, f"Expected text '{text}' not found in markdown"

    # Save output for inspection
    output_file = output_dir / f"{test_func.__name__}.md"
    output_file.write_text(markdown)

    # Additional specific assertions for sample_function
    if test_func == sample_function:
        # Check parameter table
        assert "| param1 | str |" in markdown
        assert "| param2 | int |" in markdown
        assert "dict" in markdown  # Return type should be mentioned
