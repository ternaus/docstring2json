"""Utility functions for the google-docstring-2md package."""

import inspect
import logging
from typing import Protocol, TypeVar

logger = logging.getLogger(__name__)


class HasModule(Protocol):
    """Protocol for objects that have a __module__ attribute."""

    __module__: str


T = TypeVar("T", bound=HasModule)


def get_github_url(
    obj: object,
    repo_url: str,
    branch: str = "main",
) -> str | None:
    """Generate a GitHub URL for a given class or function.

    Args:
        obj (object): The class or function object
        repo_url (str): Base URL of the GitHub repository (e.g., "https://github.com/username/repo")
        branch (str): The branch name to link to (default: "main")

    Returns:
        Union[str, None]: URL to the class or function in GitHub, or None if URL cannot be generated

    Example:
        >>> import albumentations as A
        >>> get_github_url(
        ...     A.RandomFog,
        ...     "https://github.com/albumentations-team/albumentations",
        ...     "main"
        ... )
        'https://github.com/albumentations-team/albumentations/blob/main/albumentations/augmentations/transforms.py#L5215'
    """
    # If object doesn't have a module, return None
    if not hasattr(obj, "__module__"):
        return None

    # Get the module name and create GitHub URL
    module_name = obj.__module__  # type: ignore[attr-defined]
    github_file_path = module_name.replace(".", "/") + ".py"
    github_url = f"{repo_url}/blob/{branch}/{github_file_path}"

    # Find line number through multiple methods
    line_number = _find_line_number_from_github(obj, repo_url, branch, github_file_path)
    if not line_number:
        line_number = _find_line_number_with_inspect(obj)

    # Return URL with line number if found, otherwise just URL
    if line_number:
        return f"{github_url}#L{line_number}"
    return github_url


def _find_line_number_from_github(
    obj: object,
    repo_url: str,
    branch: str,
    github_file_path: str,
) -> int | None:
    """Find line number by fetching source from GitHub.

    Args:
        obj (object): The object to find in the source
        repo_url (str): GitHub repository URL
        branch (str): Branch name
        github_file_path (str): Path to the file in the repo

    Returns:
        int | None: Line number if found, None otherwise
    """
    import urllib.error
    import urllib.parse
    import urllib.request

    # Try to fetch source code from GitHub
    try:
        # Construct URL for raw content
        raw_url = f"{repo_url.replace('github.com', 'raw.githubusercontent.com')}/{branch}/{github_file_path}"

        # Validate URL scheme for security
        parsed_url = urllib.parse.urlparse(raw_url)
        if parsed_url.scheme not in ("http", "https"):
            error_msg = f"Unsupported URL scheme: {parsed_url.scheme}"
            logger.warning(error_msg)
            return None

        # Fetch the raw file content
        try:
            # Validate protocols and create a safe request
            req = urllib.request.Request(  # noqa: S310
                raw_url,
                headers={"User-Agent": "google-docstring-2md"},
                method="GET",
            )
            with urllib.request.urlopen(req) as response:  # noqa: S310
                source_code = response.read().decode("utf-8").splitlines()
        except urllib.error.URLError as e:
            logger.warning(f"Failed to fetch source from URL: {e}")
            return None

        # Determine the search pattern based on object type
        obj_name = obj.__name__
        if inspect.isclass(obj):
            pattern = f"class {obj_name}"
        elif inspect.isfunction(obj):
            pattern = f"def {obj_name}"
        else:
            # For other objects, we can't find a line number
            return None

        # Find the line with zero indentation that matches our pattern
        for i, line in enumerate(source_code, 1):
            stripped = line.lstrip()
            # Check if it's a definition at zero indentation
            if line == stripped and stripped.startswith(pattern) and (stripped[len(pattern)] in ["(", " ", ":", "\n"]):
                return i
        # No match found in for loop
        return None  # noqa: TRY300

    except (urllib.error.URLError, urllib.error.HTTPError, ValueError):
        return None


def _find_line_number_with_inspect(obj: object) -> int | None:
    """Find line number using inspect module.

    Args:
        obj (object): The object to find the line number for

    Returns:
        int | None: Line number if found, None otherwise
    """
    try:
        return inspect.getsourcelines(obj)[1]
    except (TypeError, OSError):
        return None
