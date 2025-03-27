"""Utilities for converting Google-style docstrings to TSX.

This module provides functions to convert Python classes and functions with Google-style
docstrings into TSX documentation components.
"""

import logging
from collections.abc import Callable
from pathlib import Path

from google_docstring_parser import parse_google_docstring

from docstring_2tsx.processor import (
    build_tsx_params_table,
    format_tsx_section,
    process_description,
)
from utils.shared import (
    collect_module_members,
    collect_package_modules,
    group_modules_by_file,
    has_documentable_members,
    normalize_anchor_id,
    process_module_file,
)
from utils.signature_formatter import format_signature, get_signature_params

logger = logging.getLogger(__name__)


def get_source_line(obj: type | Callable) -> int:
    """Get the source line number for a class or function.

    Args:
        obj: Class or function to get source line for

    Returns:
        Line number in the source file
    """
    try:
        return obj.__code__.co_firstlineno
    except AttributeError:
        return 1


def class_to_tsx(obj: type | Callable, github_repo: str | None = None, branch: str = "main") -> str:
    """Convert class or function to TSX component.

    This function generates TSX documentation component for a class or function,
    extracting information from its docstring and signature.

    Args:
        obj: Class or function to document
        github_repo: Base URL of the GitHub repository (e.g., "https://github.com/username/repo")
        branch: Branch name for GitHub links (default: "main")

    Returns:
        TSX component as string
    """
    # Get object name and parameters
    obj_name = obj.__name__
    params = get_signature_params(obj)

    # Format and add the signature
    signature = format_signature(obj, params)

    # Add GitHub link if github_repo is provided
    github_section = ""
    if github_repo:
        source_line = get_source_line(obj)
        # GitHub icon SVG path split into smaller chunks
        svg_path = (
            "M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-"
            "2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87"
            ".87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-"
            "2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1."
            "92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2"
            " 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"
        )
        github_icon = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" '
            f'fill="currentColor"><path d="{svg_path}"/></svg>'
        )
        github_link = (
            f'<a href="{github_repo}/blob/{branch}/{obj.__module__.replace(".", "/")}.py#L{source_line}" '
            'className="github-source-link">View source on GitHub</a>'
        )
        github_section = (
            f'<div className="github-source-container">'
            f'<span className="github-icon">{github_icon}</span>'
            f"{github_link}"
            f"</div>"
        )

    # Parse docstring
    docstring = obj.__doc__ or ""
    parsed = parse_google_docstring(docstring)

    # Add description
    description = process_description(parsed)

    # Add parameters table if we have parameters
    param_section = ""
    if params:
        param_table = build_tsx_params_table(params, parsed)
        param_section = "\n".join(param_table)

    # Add other sections (returns, raises, etc.)
    other_sections = []
    for section, content in parsed.items():
        if section not in ["Description", "Args"]:
            section_content = format_tsx_section(section, content)
            if section_content:
                other_sections.append(section_content)

    # Join sections with newlines
    sections_str = "\n".join(
        [
            f'<pre><code className="language-python">{signature}</code></pre>',
            github_section,
            description,
            param_section,
            *other_sections,
        ],
    )

    # Create the component
    return (
        "import React from 'react';\n\n"
        f"export default function {obj_name}() {{\n"
        "  return (\n"
        '    <div className="docstring-content">\n'
        f"      {sections_str}\n"
        "    </div>\n"
        "  );\n"
        "}\n"
    )


def file_to_tsx(module: object, module_name: str, *, github_repo: str | None = None, branch: str = "main") -> str:
    """Convert a module to a single TSX document.

    Args:
        module: The module object to document
        module_name: Name of the module for the heading
        github_repo: Base URL of the GitHub repository (e.g., "https://github.com/username/repo")
        branch: Branch name for GitHub links (default: "main")

    Returns:
        str: The TSX content
    """
    # Collect module members
    classes, functions = collect_module_members(module)

    # Normalize the module_name for the anchor
    module_anchor = module_name.replace(".", "-")

    # Process classes and functions
    member_components = []
    for name, obj in sorted(classes + functions):
        # Add anchor for the item
        anchor_id = normalize_anchor_id(module_name, name)
        member_components.append(f'<a id="{anchor_id}"></a>')

        # Convert to TSX and extract the component content
        tsx = class_to_tsx(obj, github_repo=github_repo, branch=branch)
        component_content = tsx.split("return (")[1].split(");")[0].strip()
        member_components.append(component_content)

    # Join member components with newlines
    members_str = "\n".join(member_components)

    # Create the module component
    return (
        "import React from 'react';\n\n"
        f"export default function {module_name.replace('.', '_')}() {{\n"
        "  return (\n"
        "    <>\n"
        '      <div className="module-content">\n'
        f"        <h1>{module_name}</h1>\n"
        f'        <a id="{module_anchor}"></a>\n'
        f"        {members_str}\n"
        "      </div>\n"
        "    </>\n"
        "  );\n"
        "}\n"
    )


def package_to_tsx_files(
    package: object,
    output_dir: Path,
    *,
    github_repo: str | None = None,
    branch: str = "main",
) -> None:
    """Convert a package to TSX files.

    Args:
        package: Python package
        output_dir: Directory to write TSX files
        github_repo: Base URL of the GitHub repository
        branch: Branch name for GitHub links
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect all modules in the package
    modules = collect_package_modules(package)

    # Group modules by file
    module_groups = group_modules_by_file(modules)

    # Process each file
    for file_path, file_modules in module_groups.items():
        if not has_documentable_members(file_modules[0][1]):
            continue

        try:
            # Get the module name from the first module in the file
            module_name = file_modules[0][1].__name__

            # Process the file
            content = process_module_file(
                file_path,
                file_modules,
                github_repo=github_repo,
                branch=branch,
                converter_func=file_to_tsx,
            )

            # Create the Next.js page structure
            # Convert module name to path (e.g., "package.module.submodule" -> "package/module/submodule")
            page_path = output_dir / module_name.replace(".", "/")
            page_path.mkdir(parents=True, exist_ok=True)

            # Write the content to page.tsx
            output_file = page_path / "page.tsx"
            output_file.write_text(content)
        except Exception:
            logger.exception("Error processing file %s", file_path)
