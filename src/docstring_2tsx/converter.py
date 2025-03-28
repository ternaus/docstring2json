"""Utilities for converting Google-style docstrings to TSX.

This module provides functions to convert Python classes and functions with Google-style
docstrings into TSX documentation components that use imported React components.
"""

import json
import logging
from collections.abc import Callable
from pathlib import Path

from google_docstring_parser import parse_google_docstring

from docstring_2tsx.processor import (
    build_params_data,
    format_section_data,
    process_description,
)
from utils.shared import (
    collect_module_members,
    collect_package_modules,
    group_modules_by_file,
    has_documentable_members,
    process_module_file,
)
from utils.signature_formatter import format_signature, get_signature_params

logger = logging.getLogger(__name__)

# Path to import components from, could be made configurable
COMPONENTS_IMPORT_PATH = "@/components/docs"


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


def class_to_data(obj: type | Callable, github_repo: str | None = None, branch: str = "main") -> dict:
    """Convert class or function to structured data format.

    This function extracts documentation data for a class or function from
    its docstring and signature, returning a structured dictionary.

    Args:
        obj: Class or function to document
        github_repo: Base URL of the GitHub repository (e.g., "https://github.com/username/repo")
        branch: Branch name for GitHub links (default: "main")

    Returns:
        Dictionary containing structured documentation data
    """
    # Get object name and parameters
    obj_name = obj.__name__
    params = get_signature_params(obj)

    # Format signature
    signature = format_signature(obj, params)

    # Prepare GitHub link if github_repo is provided
    github_url = None
    if github_repo:
        source_line = get_source_line(obj)
        github_url = f"{github_repo}/blob/{branch}/{obj.__module__.replace('.', '/')}.py#L{source_line}"

    # Parse docstring
    docstring = obj.__doc__ or ""
    parsed = parse_google_docstring(docstring)

    # Get description
    description = process_description(parsed)

    # Get parameters data
    params_data = build_params_data(params, parsed)

    # Process other sections (returns, raises, etc.)
    sections = []
    for section, content in parsed.items():
        if section not in ["Description", "Args"]:
            section_data = format_section_data(section, content)
            if section_data:
                sections.append(section_data)

    # Create the data structure
    member_data = {
        "name": obj_name,
        "type": "class" if isinstance(obj, type) else "function",
        "signature": signature,
    }

    # Add optional fields
    if description:
        member_data["description"] = description
    if params_data:
        member_data["params"] = params_data
    if github_url:
        member_data["githubUrl"] = github_url
    if sections:
        member_data["sections"] = sections

    return member_data


def file_to_tsx(module: object, module_name: str, *, github_repo: str | None = None, branch: str = "main") -> str:
    """Convert a module to a TSX document that uses imported components.

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

    # Process classes and functions to get their data
    members_data = []
    for _name, obj in sorted(classes + functions):
        # Convert to data structure
        member_data = class_to_data(obj, github_repo=github_repo, branch=branch)
        members_data.append(member_data)

    # Create module data
    module_data = {
        "moduleName": module_name,
        "members": members_data,
    }

    # JSON representation of the data (with indentation for readability)
    module_data_str = json.dumps(module_data, indent=2)

    # Create the page.tsx file content
    components = "ModuleDoc, MemberDoc, Signature, Description, ParamsTable, GitHubLink, Section"
    return (
        f"import {{ {components} }} from '{COMPONENTS_IMPORT_PATH}';\n\n"
        "// Data structure extracted from Python docstrings\n"
        f"const moduleData = {module_data_str};\n\n"
        "export default function Page() {\n"
        "  return <ModuleDoc {...moduleData} />;\n"
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
