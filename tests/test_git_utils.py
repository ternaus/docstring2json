"""Tests for the Git utility functions in the utils module."""

import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from google_docstring_2md.utils import (
    get_git_remote_url,
    get_git_branch,
    get_github_info_from_local_repo,
)


@pytest.mark.parametrize(
    "stdout,expected_result",
    [
        # HTTPS URL
        ("https://github.com/username/repo.git\n", "https://github.com/username/repo"),
        # HTTPS URL without .git
        ("https://github.com/username/repo\n", "https://github.com/username/repo"),
        # SSH URL
        ("git@github.com:username/repo.git\n", "https://github.com/username/repo"),
        # Non-standard URL format
        ("https://example.com/repo.git\n", None),
        # Empty response
        ("", None),
    ],
)
def test_get_git_remote_url(stdout, expected_result):
    """Test the get_git_remote_url function with various git remote outputs."""
    with patch("subprocess.run") as mock_run:
        # Configure the mock
        process_mock = MagicMock()
        process_mock.stdout = stdout
        process_mock.returncode = 0 if stdout else 1
        mock_run.return_value = process_mock

        # Call the function
        result = get_git_remote_url()

        # Verify the result
        assert result == expected_result

        # Verify the subprocess call
        mock_run.assert_called_once_with(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=".",
            capture_output=True,
            text=True,
            check=False,
        )


def test_get_git_remote_url_with_custom_path():
    """Test get_git_remote_url with a custom repository path."""
    with patch("subprocess.run") as mock_run:
        # Configure the mock
        process_mock = MagicMock()
        process_mock.stdout = "https://github.com/username/repo.git\n"
        process_mock.returncode = 0
        mock_run.return_value = process_mock

        # Call the function with a custom path
        custom_path = Path("/path/to/repo")
        result = get_git_remote_url(custom_path)

        # Verify the result
        assert result == "https://github.com/username/repo"

        # Verify the subprocess call used the custom path
        mock_run.assert_called_once_with(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=custom_path,
            capture_output=True,
            text=True,
            check=False,
        )


def test_get_git_remote_url_subprocess_error():
    """Test get_git_remote_url when subprocess fails."""
    with patch("subprocess.run") as mock_run:
        # Configure the mock to raise an exception
        mock_run.side_effect = subprocess.SubprocessError("Command failed")

        # Call the function
        result = get_git_remote_url()

        # Verify the result is None
        assert result is None


def test_get_git_branch():
    """Test the get_git_branch function."""
    with patch("subprocess.run") as mock_run:
        # Configure the mock
        process_mock = MagicMock()
        process_mock.stdout = "main\n"
        process_mock.returncode = 0
        mock_run.return_value = process_mock

        # Call the function
        result = get_git_branch()

        # Verify the result
        assert result == "main"

        # Verify the subprocess call
        mock_run.assert_called_once_with(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=".",
            capture_output=True,
            text=True,
            check=False,
        )


def test_get_git_branch_error():
    """Test get_git_branch when git command fails."""
    with patch("subprocess.run") as mock_run:
        # Configure the mock
        process_mock = MagicMock()
        process_mock.returncode = 1
        process_mock.stderr = "fatal: not a git repository\n"
        mock_run.return_value = process_mock

        # Call the function
        result = get_git_branch()

        # Verify the result
        assert result is None


def test_get_github_info_from_local_repo():
    """Test the get_github_info_from_local_repo function."""
    with patch("google_docstring_2md.utils.get_git_remote_url") as mock_remote, patch(
        "google_docstring_2md.utils.get_git_branch"
    ) as mock_branch:
        # Configure the mocks
        mock_remote.return_value = "https://github.com/username/repo"
        mock_branch.return_value = "develop"

        # Call the function
        repo_url, branch = get_github_info_from_local_repo("/path/to/repo")

        # Verify the result
        assert repo_url == "https://github.com/username/repo"
        assert branch == "develop"

        # Verify the mocks were called with the right path
        mock_remote.assert_called_once_with("/path/to/repo")
        mock_branch.assert_called_once_with("/path/to/repo")


def test_get_github_info_from_local_repo_not_found():
    """Test get_github_info_from_local_repo when git info is not found."""
    with patch("google_docstring_2md.utils.get_git_remote_url") as mock_remote, patch(
        "google_docstring_2md.utils.get_git_branch"
    ) as mock_branch:
        # Configure the mocks
        mock_remote.return_value = None
        mock_branch.return_value = None

        # Call the function
        repo_url, branch = get_github_info_from_local_repo()

        # Verify the result
        assert repo_url is None
        assert branch is None
