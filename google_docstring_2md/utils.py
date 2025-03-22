"""Utility functions for the google-docstring-2md package."""

import inspect
import logging
from typing import Protocol, TypeVar

logger = logging.getLogger(__name__)

# HTTP status codes
HTTP_NOT_FOUND = 404


class HasModule(Protocol):
    """Protocol for objects that have a __module__ attribute."""

    __module__: str


T = TypeVar("T", bound=HasModule)

# Cache for GitHub source code, keyed by (repo_url, branch, file_path)
_SOURCE_CODE_CACHE: dict[tuple[str, str, str], list[str]] = {}


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
        str | None: URL to the class or function in GitHub, or None if URL cannot be generated

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

    # Get the module name and create file path
    module_name = obj.__module__  # type: ignore[attr-defined]
    github_file_path = module_name.replace(".", "/") + ".py"

    # Find line number through multiple methods
    line_number = _find_line_number_from_github_source(
        obj,
        repo_url,
        branch,
        github_file_path,
    ) or _find_line_number_with_inspect(obj)

    # Format GitHub URL
    github_url = f"{repo_url}/blob/{branch}/{github_file_path}"

    # Return URL with line number if found, otherwise just URL
    return f"{github_url}#L{line_number}" if line_number else github_url


def _get_github_source_code(repo_url: str, branch: str, github_file_path: str) -> list[str] | None:
    """Fetch source code from GitHub, with caching.

    Args:
        repo_url (str): GitHub repository URL
        branch (str): Branch name
        github_file_path (str): Path to the file in the repo

    Returns:
        list[str] | None: List of source code lines if successful, None otherwise
    """
    cache_key = (repo_url, branch, github_file_path)

    # Return from cache if available
    if cache_key in _SOURCE_CODE_CACHE:
        return _SOURCE_CODE_CACHE[cache_key]

    # Handle GitHub URL case
    return _get_source_from_github(repo_url, branch, github_file_path, cache_key)


def _get_source_from_github(
    repo_url: str,
    branch: str,
    github_file_path: str,
    cache_key: tuple[str, str, str],
) -> list[str] | None:
    """Fetch source code from GitHub.

    Args:
        repo_url (str): GitHub repository URL
        branch (str): Branch name
        github_file_path (str): Path to the file within the repository
        cache_key (tuple): Cache key for storing the result

    Returns:
        list[str] | None: List of source code lines if successful, None otherwise
    """
    import urllib.error
    import urllib.parse
    import urllib.request

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

            # Cache the result
            _SOURCE_CODE_CACHE[cache_key] = source_code
            return source_code
        except urllib.error.HTTPError as e:
            # If it's a 404 error, it might be because this GitHub URL was derived from a local repository
            # In this case, we'll log at debug level since we might be using local files directly
            if e.code == HTTP_NOT_FOUND:
                logger.debug(f"HTTP 404 Not Found for URL: {raw_url}")
            else:
                logger.warning(f"Failed to fetch source from URL: {e}")
            return None
        except urllib.error.URLError as e:
            logger.warning(f"Failed to fetch source from URL: {e}")
            return None

    except (urllib.error.URLError, urllib.error.HTTPError, ValueError):
        return None


def _find_line_number_from_github_source(
    obj: object,
    repo_url: str,
    branch: str,
    github_file_path: str,
) -> int | None:
    """Find line number in GitHub source code.

    Args:
        obj (object): The object to find in the source
        repo_url (str): GitHub repository URL or path to local repository
        branch (str): Branch name
        github_file_path (str): Path to the file in the repo

    Returns:
        int | None: Line number if found, None otherwise
    """
    # Get the source code (cached if already fetched)
    source_code = _get_github_source_code(repo_url, branch, github_file_path)
    if not source_code:
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


def clear_github_source_cache() -> None:
    """Clear the GitHub source code cache.

    This can be useful if you're working with multiple repositories or branches.
    """
    _SOURCE_CODE_CACHE.clear()
