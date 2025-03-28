"""Utilities for GitHub integration.

This module provides functions to generate GitHub links for source code.
"""

import inspect
from dataclasses import dataclass

# Cache for GitHub source code to avoid repeated requests
_SOURCE_CODE_CACHE: dict[tuple[str, str, str], list[str]] = {}


def clear_github_source_cache() -> None:
    """Clear the GitHub source code cache."""
    _SOURCE_CODE_CACHE.clear()


def get_github_url(obj: object, github_repo: str, branch: str = "main") -> str | None:
    """Get GitHub URL for an object's source code.

    Args:
        obj (object): Object to get URL for
        github_repo (str): Base URL of the GitHub repository
        branch (str): Branch name to link to

    Returns:
        Optional[str]: GitHub URL or None if not found
    """
    if not hasattr(obj, "__module__"):
        return None

    try:
        # Get the source file and line number
        lines, start_line = inspect.getsourcelines(obj)
        module = obj.__module__.replace(".", "/")
        return f"{github_repo}/blob/{branch}/{module}.py#L{start_line}"
    except (OSError, TypeError):
        # If we can't get the source lines, return URL without line number
        module = obj.__module__.replace(".", "/")
        return f"{github_repo}/blob/{branch}/{module}.py"


@dataclass
class GitHubConfig:
    """Configuration for GitHub integration."""

    github_repo: str | None = None
    branch: str = "main"

    def __post_init__(self) -> None:
        """Initialize GitHub configuration."""
        # No special handling needed - only accept GitHub URLs
