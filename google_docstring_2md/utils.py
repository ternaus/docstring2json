"""Utility functions for the google-docstring-2md package."""

import inspect
from typing import Protocol, TypeVar


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
    if not hasattr(obj, "__module__"):
        return None

    # Get the module name
    module_name = obj.__module__  # type: ignore[attr-defined]

    # Convert module path to file path
    file_path = module_name.replace(".", "/") + ".py"

    try:
        # Get the line number where the object is defined
        line_number = inspect.getsourcelines(obj)[1]
    except (TypeError, OSError):
        # If we can't get the source lines, just link to the file without line number
        return f"{repo_url}/blob/{branch}/{file_path}"
    else:
        # Create the GitHub URL with line number
        return f"{repo_url}/blob/{branch}/{file_path}#L{line_number}"
