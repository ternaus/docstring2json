"""Google docstring to Markdown converter.

This package provides utilities to convert Python classes and functions with Google-style
docstrings into Markdown documentation.
"""

from google_docstring_2md.converter import (
    class_to_markdown,
    file_to_markdown,
)
from google_docstring_2md.docstring_processor import (
    escape_mdx_special_chars,
    format_section_content,
)
from google_docstring_2md.document_tree import (
    package_to_markdown_structure,
)
from google_docstring_2md.github_linker import (
    GitHubConfig,
)
from google_docstring_2md.signature_formatter import (
    Parameter,
    format_signature,
    get_signature_params,
)
from google_docstring_2md.utils import (
    clear_github_source_cache,
    get_github_url,
)

__all__ = [
    "GitHubConfig",
    "Parameter",
    "class_to_markdown",
    "clear_github_source_cache",
    "escape_mdx_special_chars",
    "file_to_markdown",
    "format_section_content",
    "format_signature",
    "get_github_url",
    "get_signature_params",
    "package_to_markdown_structure",
]
