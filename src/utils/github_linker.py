"""Utilities for GitHub integration.

This module provides functions and classes to generate GitHub links and
handle GitHub integration for markdown documentation.
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


def add_github_link(sections: list[str], obj: object, github_repo: str | None, branch: str) -> None:
    """Add GitHub link to the documentation sections.

    Args:
        sections (list[str]): List of documentation sections to modify
        obj (object): The object being documented
        github_repo (str | None): GitHub repository URL
        branch (str): Branch name

    Returns:
        None: Modifies the sections list in-place
    """
    if github_repo:
        github_url = get_github_url(obj, github_repo, branch)
        if github_url:
            # GitHub SVG icon (simplified)
            github_icon = (
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" '
                'fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 '
                "0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53"
                ".63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 "
                "0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36"
                ".09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75"
                "-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42"
                '-3.58-8-8-8z"/></svg>'
            )

            # Enhanced GitHub link with class that can be styled at the Docusaurus level
            sections.append(
                f'<div className="github-source-container">\n'
                f'  <span className="github-icon">{github_icon}</span>\n'
                f'  <a href="{github_url}" className="github-source-link">View source on GitHub</a>\n'
                f"</div>\n\n",
            )
