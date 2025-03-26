"""Tests for GitHub URL generation in the utils module."""

import pytest

from src.utils.github_linker import clear_github_source_cache, _SOURCE_CODE_CACHE


def test_clear_github_source_cache():
    """Test clearing the GitHub source code cache."""
    # Add an item to the cache
    _SOURCE_CODE_CACHE[("https://github.com/user/repo", "main", "file.py")] = ["line 1", "line 2"]

    # Make sure the cache has something in it
    assert len(_SOURCE_CODE_CACHE) > 0

    # Clear the cache
    clear_github_source_cache()

    # Verify the cache is empty
    assert len(_SOURCE_CODE_CACHE) == 0
