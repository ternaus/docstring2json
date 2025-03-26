"""Tests for the utils module."""

import inspect
import pytest

from src.utils.github_linker import get_github_url


# Create a dummy class and function for testing
class DummyClass:
    """A dummy class for testing."""

    def dummy_method(self):
        """A dummy method for testing."""
        pass


def dummy_function():
    """A dummy function for testing."""
    pass


# Define a simple mock for inspect.getsourcelines that returns a known line number
def mock_getsourcelines(obj):
    """Mock version of inspect.getsourcelines that returns a predictable line number."""
    return (["line1", "line2"], 42)


# Define a mock that raises an exception
def mock_getsourcelines_error(obj):
    """Mock version of inspect.getsourcelines that raises an exception."""
    raise OSError("Cannot get source")


@pytest.mark.parametrize(
    "obj,repo_url,branch,expected_result,monkeypatch_func",
    [
        # Test with a class
        (
            DummyClass,
            "https://github.com/user/repo",
            "main",
            "https://github.com/user/repo/blob/main/tests/test_utils.py#L42",
            mock_getsourcelines,
        ),
        # Test with a function
        (
            dummy_function,
            "https://github.com/user/repo",
            "main",
            "https://github.com/user/repo/blob/main/tests/test_utils.py#L42",
            mock_getsourcelines,
        ),
        # Test with a different branch
        (
            DummyClass,
            "https://github.com/user/repo",
            "develop",
            "https://github.com/user/repo/blob/develop/tests/test_utils.py#L42",
            mock_getsourcelines,
        ),
        # Test when getsourcelines fails
        (
            DummyClass,
            "https://github.com/user/repo",
            "main",
            "https://github.com/user/repo/blob/main/tests/test_utils.py",
            mock_getsourcelines_error,
        ),
        # Test with an object that doesn't have __module__
        (
            42,  # Integer doesn't have __module__
            "https://github.com/user/repo",
            "main",
            None,
            None,  # No need to monkeypatch for this case
        ),
    ],
)
def test_get_github_url(obj, repo_url, branch, expected_result, monkeypatch_func, monkeypatch):
    """Test the get_github_url function with various inputs."""
    # Apply the monkeypatch if provided
    if monkeypatch_func:
        monkeypatch.setattr(inspect, "getsourcelines", monkeypatch_func)

    # Call the function
    result = get_github_url(obj, repo_url, branch)

    # Assert the result
    assert result == expected_result
