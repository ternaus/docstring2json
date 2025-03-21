"""Tests for the GitHubConfig class."""

from pathlib import Path
from unittest.mock import patch

import pytest

from google_docstring_2md.converter import GitHubConfig


def test_github_config_defaults():
    """Test GitHubConfig with default values."""
    config = GitHubConfig()
    assert config.github_repo is None
    assert config.branch == "main"


def test_github_config_explicit_url():
    """Test GitHubConfig with explicit GitHub URL."""
    config = GitHubConfig(
        github_repo="https://github.com/username/repo",
        branch="develop",
    )
    assert config.github_repo == "https://github.com/username/repo"
    assert config.branch == "develop"


def test_github_config_local_repo_detection():
    """Test GitHubConfig auto-detecting GitHub info from local repo path."""
    with patch("google_docstring_2md.converter.get_github_info_from_local_repo") as mock_get_info:
        # Configure the mock to return GitHub info
        mock_get_info.return_value = ("https://github.com/user/detected-repo", "detected-branch")

        # Create a config with a local path as github_repo
        config = GitHubConfig(github_repo="/path/to/repo")

        # Verify the config used the detected values
        assert config.github_repo == "https://github.com/user/detected-repo"
        assert config.branch == "detected-branch"

        # Verify the function was called with the right path
        mock_get_info.assert_called_once_with("/path/to/repo")


def test_github_config_url_not_modified():
    """Test that URLs are not processed as local paths."""
    with patch("google_docstring_2md.converter.get_github_info_from_local_repo") as mock_get_info:
        # This mock should not be called
        mock_get_info.return_value = ("https://github.com/user/detected-repo", "detected-branch")

        # Create a config with a URL
        config = GitHubConfig(github_repo="https://github.com/user/explicit-repo")

        # Verify the URL remains unchanged
        assert config.github_repo == "https://github.com/user/explicit-repo"
        assert config.branch == "main"

        # Verify the detection function was not called
        mock_get_info.assert_not_called()


def test_github_config_local_detection_with_branch():
    """Test that branch from local repo is only used if default branch is used."""
    with patch("google_docstring_2md.converter.get_github_info_from_local_repo") as mock_get_info:
        # Configure the mock
        mock_get_info.return_value = ("https://github.com/user/detected-repo", "detected-branch")

        # Create a config with explicit branch and local path
        config = GitHubConfig(github_repo="/path/to/repo", branch="explicit-branch")

        # Verify github_repo is detected but branch is from explicit value
        assert config.github_repo == "https://github.com/user/detected-repo"
        assert config.branch == "explicit-branch"

        # Verify the detection function was called
        mock_get_info.assert_called_once_with("/path/to/repo")


def test_github_config_local_detection_failure():
    """Test behavior when local repo detection fails."""
    with patch("google_docstring_2md.converter.get_github_info_from_local_repo") as mock_get_info:
        # Configure the mock to return None values (detection failure)
        mock_get_info.return_value = (None, None)

        # Create a config with a local path
        config = GitHubConfig(github_repo="/path/to/repo")

        # The github_repo should remain as the path if detection failed
        assert config.github_repo == "/path/to/repo"
        assert config.branch == "main"

        # Verify the detection function was called
        mock_get_info.assert_called_once_with("/path/to/repo")


def test_github_config_with_pathlib_path():
    """Test GitHubConfig with a Path object for github_repo."""
    with patch("google_docstring_2md.converter.get_github_info_from_local_repo") as mock_get_info:
        # Configure the mock
        mock_get_info.return_value = ("https://github.com/user/detected-repo", "detected-branch")

        # Create a config with a Path object
        path_obj = Path("/path/to/repo")
        config = GitHubConfig(github_repo=path_obj)

        # Verify the config used the detected values
        assert config.github_repo == "https://github.com/user/detected-repo"
        assert config.branch == "detected-branch"

        # Verify the function was called with the Path object
        mock_get_info.assert_called_once_with(path_obj)
