"""Google docstring to Markdown converter.

This package provides utilities to convert Python classes and functions with Google-style
docstrings into Markdown documentation.
"""

from google_docstring_2md.converter import (
    class_to_markdown,
    file_to_markdown,
)
from google_docstring_2md.document_tree import (
    package_to_markdown_structure,
)

__all__ = ["class_to_markdown", "file_to_markdown", "package_to_markdown_structure"]
