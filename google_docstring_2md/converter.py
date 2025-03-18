"""Utilities for converting Google-style docstrings to Markdown.

This module provides functions to convert Python classes and functions with Google-style
docstrings into Markdown documentation.
"""

import importlib
import inspect
import logging
import pkgutil
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from google_docstring_parser import parse_google_docstring
from tqdm import tqdm

logger = logging.getLogger(__name__)


@dataclass
class Parameter:
    """Parameter information extracted from signature and docstring."""

    name: str
    type: str
    default: Any
    description: str = ""


def get_signature_params(obj: type | Callable) -> list[Parameter]:
    """Extract parameters from object signature.

    Args:
        obj (Union[type, Callable]): Class or function to extract parameters from

    Returns:
        List of Parameter objects containing name, type, default value
    """
    signature = inspect.signature(obj)
    params = []

    for name, param in signature.parameters.items():
        # Get parameter type annotation
        if param.annotation is not inspect.Signature.empty:
            if hasattr(param.annotation, "__name__"):
                param_type = param.annotation.__name__
            else:
                param_type = str(param.annotation).replace("typing.", "")
                # Clean up typing annotations (remove typing. prefix)
                if "'" in param_type:
                    param_type = param_type.split("'")[1]
        else:
            param_type = ""

        # Get default value
        default = param.default if param.default is not inspect.Signature.empty else None

        params.append(Parameter(name=name, type=param_type, default=default))

    return params


def format_default_value(value: object) -> str:
    """Format default value for signature display.

    Args:
        value (object): Parameter default value

    Returns:
        Formatted string representation of the value
    """
    if value is None:
        return "None"
    if isinstance(value, str):
        return f"'{value}'"
    return str(value)


def format_section_content(section: str, content: str) -> str:
    """Format section content, handling special cases like code examples.

    Args:
        section (str): Section name (e.g. "Examples", "Notes")
        content (str): Raw section content

    Returns:
        Formatted content with proper markdown
    """
    if section in ["Example", "Examples"] and (">>>" in content or "..." in content):
        lines = []
        for line_content in content.split("\n"):
            line_stripped = line_content.strip()
            if line_stripped.startswith((">>> ", "... ")):
                lines.append(line_stripped[4:])
            elif line_stripped:
                lines.append(line_stripped)
        return "```python\n" + "\n".join(lines) + "\n```"
    return content


def _format_signature(obj: type | Callable, params: list[Parameter]) -> str:
    """Format object signature for documentation.

    Args:
        obj (Union[type, Callable]): Class or function object
        params (list[Parameter]): List of parameters

    Returns:
        Formatted signature as string
    """
    # Format signature
    param_str = ", ".join(f"{p.name}={format_default_value(p.default)}" for p in params)
    signature = f"{obj.__name__}({param_str})"

    # Handle return annotation for functions
    if inspect.isfunction(obj) and obj.__annotations__.get("return"):
        return_type = obj.__annotations__["return"]
        signature += f" -> {return_type.__name__ if hasattr(return_type, '__name__') else str(return_type)}"

    return signature


def _process_description(parsed: dict) -> str:
    """Process description section from parsed docstring.

    Args:
        parsed (dict): Parsed docstring dictionary

    Returns:
        Formatted description as string
    """
    if "Description" not in parsed:
        return ""

    desc = parsed["Description"]
    if not isinstance(desc, str):
        desc = str(desc)
    return f"{desc}\n"


def _extract_param_docs(param: Parameter, param_docs: dict, obj: type | Callable) -> tuple[str, str]:
    """Extract parameter documentation info.

    Args:
        param (Parameter): Parameter object
        param_docs (dict): Dictionary mapping parameter names to docstring info
        obj (Union[type, Callable]): Class or function object

    Returns:
        Tuple of (type, description)
    """
    # Get parameter description from docstring or use empty string
    desc = ""
    param_name = param.name

    # If our parameter is in the docstring, use that info
    if param_name in param_docs:
        desc = param_docs[param_name].get("description", "")
        if not isinstance(desc, str):
            desc = str(desc)
        desc = desc.replace("\n", " ")

        # Get type from docstring if available
        doc_type = param_docs[param_name].get("type", "")
    else:
        # If parameter not found in docstring, use type from signature
        doc_type = param.type

    # If no type could be found, check annotations
    if not doc_type and param_name in obj.__annotations__:
        annotation = obj.__annotations__[param_name]
        if hasattr(annotation, "__name__"):
            doc_type = annotation.__name__
        else:
            doc_type = str(annotation).replace("typing.", "")
            if "'" in doc_type:
                doc_type = doc_type.split("'")[1]

    if not isinstance(doc_type, str):
        doc_type = str(doc_type)

    return doc_type, desc


def _build_params_table(params: list[Parameter], parsed: dict, obj: type | Callable) -> list[str]:
    """Build parameters table from parameter information.

    Args:
        params (list[Parameter]): List of parameter objects
        parsed (dict): Parsed docstring dictionary
        obj (Union[type, Callable]): Class or function object

    Returns:
        List of markdown strings for parameter table
    """
    if not parsed.get("Args"):
        return []

    result = [
        "\n## Parameters\n",
        "| Name | Type | Description |\n",
        "|------|------|-------------|\n",
    ]

    # Create a dictionary to lookup parameter info from docstring
    param_docs = {arg["name"]: arg for arg in parsed["Args"]}

    for param in params:
        doc_type, desc = _extract_param_docs(param, param_docs, obj)
        result.append(f"| {param.name} | {doc_type} | {desc} |\n")

    return result


def _process_other_sections(parsed: dict) -> list[str]:
    """Process sections other than Description and Args.

    Args:
        parsed (dict): Parsed docstring dictionary

    Returns:
        List of markdown strings for the other sections
    """
    result = []

    for section, section_content in parsed.items():
        if section not in ["Description", "Args"]:
            if not isinstance(section_content, str):
                if isinstance(section_content, list) and not section_content:
                    continue
                processed_content = str(section_content)
            else:
                processed_content = section_content

            result.extend(
                [
                    f"\n## {section}\n",
                    format_section_content(section, processed_content),
                    "\n",
                ],
            )

    return result


def class_to_markdown(obj: type | Callable) -> str:
    """Convert class or function to markdown documentation.

    This function generates markdown documentation for a class or function,
    extracting information from its docstring and signature.

    Args:
        obj (Union[type, Callable]): Class or function to document

    Returns:
        Markdown formatted documentation string
    """
    sections = []

    # Get object name and parameters
    obj_name = obj.__name__
    params = get_signature_params(obj)

    # Format and add the signature
    signature = _format_signature(obj, params)
    sections.extend(
        [
            f"# {obj_name}\n",
            f"```python\n{signature}\n```\n",
        ],
    )

    # Parse docstring
    docstring = obj.__doc__ or ""
    parsed = parse_google_docstring(docstring)

    # Add description
    description = _process_description(parsed)
    if description:
        sections.append(description)

    # Add parameters table
    param_table = _build_params_table(params, parsed, obj)
    sections.extend(param_table)

    # Add remaining sections
    other_sections = _process_other_sections(parsed)
    sections.extend(other_sections)

    return "".join(sections)


def generate_markdown_files(package: object, output_dir: Path) -> None:
    """Generate markdown files for all classes in a package.

    Args:
        package (object): Python package or module
        output_dir (Path): Directory to write markdown files
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, obj in inspect.getmembers(package):
        if inspect.isclass(obj) and obj.__module__.startswith(package.__name__):
            markdown = class_to_markdown(obj)
            output_file = output_dir / f"{name}.md"
            output_file.write_text(markdown)


def module_to_markdown_files(
    module: object,
    output_dir: Path,
    *,
    exclude_private: bool = False,
) -> None:
    """Generate markdown files for all classes and functions in a module.

    Args:
        module (object): Python module
        output_dir (Path): Directory to write markdown files
        exclude_private (bool): Whether to exclude private classes and methods (starting with _)
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process classes and functions
    for name, obj in inspect.getmembers(module):
        # Skip private members if exclude_private is True
        if exclude_private and name.startswith("_"):
            continue

        # Only consider classes and functions defined in this module
        # or directly assigned to this module
        is_in_module = (hasattr(obj, "__module__") and obj.__module__ == module.__name__) or (
            inspect.isclass(obj) or inspect.isfunction(obj)
        )

        if is_in_module:
            try:
                markdown = class_to_markdown(obj)
                output_file = output_dir / f"{name}.md"
                output_file.write_text(markdown)
            except (ValueError, TypeError, AttributeError):
                logger.exception("Error processing %s", name)


def _collect_module_members(module: object) -> tuple[list[tuple[str, object]], list[tuple[str, object]]]:
    """Collect classes and functions from a module.

    Args:
        module (object): Module to process

    Returns:
        Tuple containing lists of (name, object) pairs for classes and functions
    """
    classes = []
    functions = []

    for name, obj in inspect.getmembers(module):
        if name.startswith("_"):
            continue

        if hasattr(obj, "__module__") and obj.__module__ == module.__name__:
            if inspect.isclass(obj):
                classes.append((name, obj))
            elif inspect.isfunction(obj):
                functions.append((name, obj))

    return classes, functions


def _build_table_of_contents(classes: list[tuple[str, object]], functions: list[tuple[str, object]]) -> str:
    """Build a table of contents for the markdown document.

    Args:
        classes (list): List of (name, object) pairs for classes
        functions (list): List of (name, object) pairs for functions

    Returns:
        Markdown formatted table of contents
    """
    toc = ["## Contents\n\n"]

    # Add classes to ToC
    if classes:
        toc.append("### Classes\n\n")
        for name, _ in sorted(classes):
            toc.append(f"- [{name}](#{name.lower()})\n")
        toc.append("\n")

    # Add functions to ToC
    if functions:
        toc.append("### Functions\n\n")
        for name, _ in sorted(functions):
            toc.append(f"- [{name}](#{name.lower()})\n")
        toc.append("\n")

    return "".join(toc)


def _process_documentation_items(items: list[tuple[str, object]], section_title: str) -> str:
    """Process a list of documentation items (classes or functions).

    Args:
        items (list): List of (name, object) pairs to document
        section_title (str): Section title (e.g., "Classes" or "Functions")

    Returns:
        Markdown formatted documentation for the items
    """
    if not items:
        return ""

    content = [f"## {section_title}\n\n"]

    for _name, obj in sorted(items):
        md = class_to_markdown(obj)

        # Adjust heading level
        lines = md.split("\n")
        if lines and lines[0].startswith("# "):
            lines[0] = "### " + lines[0][2:]

        content.append("\n".join(lines) + "\n\n")

    return "".join(content)


def file_to_markdown(module: object, module_name: str) -> str:
    """Convert a module to a single markdown document.

    Args:
        module (object): The module object to document
        module_name (str): Name of the module for the heading

    Returns:
        str: The markdown content
    """
    # Collect module members
    classes, functions = _collect_module_members(module)

    # Build document sections
    content = [f"# {module_name}\n\n"]

    # Add table of contents
    content.append(_build_table_of_contents(classes, functions))

    # Add class documentation
    content.append(_process_documentation_items(classes, "Classes"))

    # Add function documentation
    content.append(_process_documentation_items(functions, "Functions"))

    return "".join(content)


def _process_mock_package(
    package: object,
    package_name: str,
    output_dir: Path,
    *,
    exclude_private: bool,
) -> None:
    """Process a mock package that doesn't have a __path__ attribute.

    Args:
        package (object): The package object
        package_name (str): Name of the package
        output_dir (Path): Root directory for output
        exclude_private (bool): Whether to exclude private classes and methods
    """
    logger.info(f"Processing mock package {package_name}")
    # Process the root module directly
    module_to_markdown_files(package, output_dir, exclude_private=exclude_private)

    # Check if there are submodules as direct attributes
    for _name, obj in inspect.getmembers(package):
        if inspect.ismodule(obj) and obj.__name__.startswith(package_name + "."):
            # Create subdirectory for submodule
            rel_name = obj.__name__[len(package_name) + 1 :]
            sub_dir = output_dir / rel_name
            sub_dir.mkdir(exist_ok=True, parents=True)
            module_to_markdown_files(obj, sub_dir, exclude_private=exclude_private)


def _collect_package_modules(
    package: object,
    package_name: str,
    *,
    exclude_private: bool,
) -> list[tuple[object, str]]:
    """Collect all modules in a package.

    Args:
        package (object): The package object
        package_name (str): Name of the package
        exclude_private (bool): Whether to exclude private modules

    Returns:
        list: List of (module, module_name) tuples
    """
    modules_to_process = []

    # Process the root module
    if hasattr(package, "__file__") and package.__file__:
        modules_to_process.append((package, package.__name__))
        logger.debug(f"Added root module: {package.__name__} from {package.__file__}")

    # Find all submodules recursively using a queue
    modules_to_explore = [(package, package_name)]
    explored_modules = set()

    while modules_to_explore:
        current_package, current_name = modules_to_explore.pop(0)
        if current_name in explored_modules:
            continue

        explored_modules.add(current_name)

        if not hasattr(current_package, "__path__"):
            continue

        logger.debug(f"Scanning for submodules in {current_name}, path: {current_package.__path__}")

        for _module_finder, module_name, is_pkg in pkgutil.iter_modules(current_package.__path__, current_name + "."):
            logger.debug(f"Found submodule: {module_name}, is_package: {is_pkg}")

            if exclude_private and any(part.startswith("_") for part in module_name.split(".")):
                logger.debug(f"Skipping private module: {module_name}")
                continue

            try:
                module = importlib.import_module(module_name)
                if hasattr(module, "__file__") and module.__file__:
                    modules_to_process.append((module, module_name))
                    logger.debug(f"Added module: {module_name} from {module.__file__}")

                    # If this is a package, add it to the exploration queue
                    if is_pkg:
                        modules_to_explore.append((module, module_name))
            except (ImportError, AttributeError):
                logger.exception(f"Failed to import module {module_name}")

    logger.debug(f"Collected {len(modules_to_process)} modules in total")
    return modules_to_process


def _group_modules_by_file(
    modules: list[tuple[object, str]],
) -> dict[str, list[tuple[object, str]]]:
    """Group modules by their file path.

    Args:
        modules (list): List of (module, module_name) tuples

    Returns:
        dict: Dictionary mapping file paths to lists of (module, module_name) tuples
    """
    file_to_modules = defaultdict(list)

    for module, module_name in modules:
        if hasattr(module, "__file__") and module.__file__:
            file_to_modules[module.__file__].append((module, module_name))

    return file_to_modules


def _process_module_file(
    file_path: str,
    modules: list[tuple[object, str]],
    output_dir: Path,
    *,
    exclude_private: bool,
) -> None:
    """Process a module file and generate markdown documentation.

    Args:
        file_path (str): Path to the module file
        modules (list): List of (module, module_name) tuples for this file
        output_dir (Path): Root directory for output
        exclude_private (bool): Whether to exclude private classes and methods
    """
    try:
        # Get the file name without extension
        path_obj = Path(file_path)
        file_name = path_obj.stem

        logger.debug(f"Processing {file_path}, stem: {file_name}")

        # Skip __init__ files with no content
        if file_name == "__init__" and not _has_documentable_members(
            modules[0][0],
            exclude_private=exclude_private,
        ):
            logger.debug(f"Skipping empty __init__ file: {file_path}")
            return None

        # Determine the module path for directory structure
        # Use the module with the shortest name to determine the path
        module, module_name = min(modules, key=lambda x: len(x[1]))
        logger.debug(f"Using module {module_name} for path structure")

        # Split the module name to get the path components
        parts = module_name.split(".")
        logger.debug(f"Module path parts: {parts}")

        # Extract the path components excluding the root package and current module name
        # First component is the package name, last component is often the module name
        if len(parts) > 1:
            # Extract everything except the first component (root package)
            simplified_path = parts[1:]

            # If the last component matches the file_name, remove it
            if simplified_path and simplified_path[-1] == file_name:
                simplified_path = simplified_path[:-1]

            # Also remove any __init__ components
            simplified_path = [part for part in simplified_path if part != "__init__"]
        else:
            simplified_path = []

        logger.debug(f"Simplified path: {simplified_path}")

        # Create the output directory path
        module_dir = output_dir
        if simplified_path:
            module_dir = output_dir.joinpath(*simplified_path)
            logger.debug(f"Creating directory: {module_dir}")
            module_dir.mkdir(exist_ok=True, parents=True)
        else:
            logger.debug(f"Using root directory: {module_dir}")

        # Generate markdown content
        try:
            md_content = file_to_markdown(module, module_name)

            # Write to file
            output_file = module_dir / f"{file_name}.md"
            logger.debug(f"Writing to file: {output_file}")
            output_file.write_text(md_content)
        except (ValueError, TypeError, AttributeError):
            logger.exception(f"Failed to generate markdown for module {module_name}")
            return False
        else:
            return True
    except (ValueError, TypeError, AttributeError):
        logger.exception(f"Error processing file {file_path}")
        return False


def package_to_markdown_structure(
    package_name: str,
    output_dir: Path,
    *,
    exclude_private: bool = False,
) -> None:
    """Convert installed package to markdown files with directory structure.

    This function imports the package, detects all modules and submodules, and
    generates markdown documentation for each file, while preserving the directory structure.
    Progress is reported with a tqdm progress bar.

    Args:
        package_name (str): Name of installed package
        output_dir (Path): Root directory for output markdown files
        exclude_private (bool): Whether to exclude private classes and methods (starting with _)
    """
    try:
        # Import the package
        package = importlib.import_module(package_name)
        output_dir.mkdir(exist_ok=True, parents=True)

        # Special handling for test mock packages that don't have __path__
        if not hasattr(package, "__path__"):
            _process_mock_package(package, package_name, output_dir, exclude_private=exclude_private)
            return

        # Collect all modules in the package
        logger.info(f"Collecting modules in {package_name}...")
        modules_to_process = _collect_package_modules(package, package_name, exclude_private=exclude_private)

        # Debug output for modules collected
        logger.debug(f"Total modules collected: {len(modules_to_process)}")
        for module, module_name in modules_to_process:
            logger.debug(f"Module: {module_name} from {getattr(module, '__file__', 'Unknown file')}")

        # Group modules by file
        file_to_modules = _group_modules_by_file(modules_to_process)

        # Debug output for file grouping
        logger.debug(f"Total files to process: {len(file_to_modules)}")
        for file_path, modules in file_to_modules.items():
            logger.debug(f"File: {file_path} with {len(modules)} modules")
            for _module, module_name in modules:
                logger.debug(f"  - Module: {module_name}")

        # Process each file and generate markdown
        logger.info(f"Processing {len(file_to_modules)} files...")
        success_count = 0
        error_count = 0

        for file_path, modules in tqdm(file_to_modules.items(), desc="Generating markdown"):
            logger.debug(f"Processing file: {file_path}")
            try:
                result = _process_module_file(file_path, modules, output_dir, exclude_private=exclude_private)
                if result:
                    success_count += 1
                else:
                    error_count += 1
            except (ValueError, TypeError, AttributeError, ImportError, OSError):
                logger.exception(f"Error processing file {file_path}")
                error_count += 1

        logger.info(
            f"Documentation generation complete. Processed {len(file_to_modules)} files: "
            f"{success_count} successful, {error_count} with errors.",
        )

    except ImportError:
        logger.exception(f"Could not import package '{package_name}'")
    except (ValueError, TypeError, AttributeError):
        logger.exception(f"Error processing package '{package_name}'")


def _has_documentable_members(
    module: object,
    *,
    exclude_private: bool,
) -> bool:
    """Check if a module has documentable members.

    Args:
        module (object): Module to check
        exclude_private (bool): Whether to exclude private members

    Returns:
        bool: True if the module has documentable members
    """
    for name, obj in inspect.getmembers(module):
        if exclude_private and name.startswith("_"):
            continue

        if (
            (inspect.isclass(obj) or inspect.isfunction(obj))
            and hasattr(obj, "__module__")
            and obj.__module__ == module.__name__
        ):
            return True

    return False
