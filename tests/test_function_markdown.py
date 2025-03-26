import pytest
from pathlib import Path

from src.docstring_2md.converter import class_to_markdown


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
