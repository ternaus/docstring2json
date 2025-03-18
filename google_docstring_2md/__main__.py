"""Command-line interface for google-docstring-2md.

This module provides a command-line interface to convert Google-style docstrings to Markdown.
"""

import argparse
import importlib
import logging
import pkgutil
import sys
from pathlib import Path

from google_docstring_2md.converter import package_to_markdown_structure

# Create a module logger
logger = logging.getLogger(__name__)


def setup_logging(verbose: bool) -> None:
    """Set up logging configuration.

    Args:
        verbose (bool): Whether to enable verbose logging
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Ensure all loggers are set to the correct level
    if verbose:
        # Set the level for our package loggers
        package_logger = logging.getLogger("google_docstring_2md")
        package_logger.setLevel(logging.DEBUG)

        # Add a stream handler if none exists
        if not package_logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            package_logger.addHandler(handler)


def _log_package_basic_info(package: object, package_name: str) -> None:
    """Log basic information about a package.

    Args:
        package (object): The package object
        package_name (str): Name of the package
    """
    logger.debug(f"Package: {package_name}")
    logger.debug(f"Has __path__: {hasattr(package, '__path__')}")

    if hasattr(package, "__path__"):
        logger.debug(f"__path__: {package.__path__}")

    logger.debug(f"Has __file__: {hasattr(package, '__file__')}")

    if hasattr(package, "__file__"):
        logger.debug(f"__file__: {package.__file__}")


def _log_first_level_modules(package: object) -> int:
    """Log first-level modules in a package.

    Args:
        package (object): The package object

    Returns:
        int: Count of found modules
    """
    logger.debug("Submodules:")
    count = 0

    if hasattr(package, "__path__"):
        for _finder, name, ispkg in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
            count += 1
            logger.debug(f"  - {name} (is_package: {ispkg})")

    logger.debug(f"Total submodules found: {count}")
    return count


def _log_second_level_modules(package: object) -> int:
    """Log second-level modules in a package.

    Args:
        package (object): The package object

    Returns:
        int: Count of found modules
    """
    logger.debug("Second-level submodules:")
    second_level_count = 0

    if hasattr(package, "__path__"):
        for _finder, name, ispkg in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
            if ispkg:
                try:
                    subpackage = importlib.import_module(name)
                    if hasattr(subpackage, "__path__"):
                        for _subfinder, subname, subispkg in pkgutil.iter_modules(
                            subpackage.__path__,
                            name + ".",
                        ):
                            second_level_count += 1
                            logger.debug(f"  - {subname} (is_package: {subispkg})")
                except ImportError:
                    logger.warning(f"  - Error importing {name}")

    logger.debug(f"Total second-level submodules found: {second_level_count}")
    return second_level_count


def debug_package_structure(package_name: str) -> None:
    """Debug the package structure by inspecting its modules and submodules.

    Args:
        package_name (str): Name of the package to inspect
    """
    logger.debug("Debug mode enabled - direct debug output")

    try:
        package = importlib.import_module(package_name)

        # Log basic package information
        _log_package_basic_info(package, package_name)

        # Log first level modules
        _log_first_level_modules(package)

        # Log second level modules
        _log_second_level_modules(package)

    except (ImportError, AttributeError, ModuleNotFoundError):
        logger.exception("Error inspecting package")


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Convert Google-style docstrings to Markdown documentation",
    )

    parser.add_argument(
        "package",
        help="Name of the package to document",
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        default="./docs",
        help="Output directory for markdown files (default: ./docs)",
    )

    parser.add_argument(
        "--exclude-private",
        action="store_true",
        help="Exclude private classes and methods (starting with _)",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable direct debug output",
    )

    return parser.parse_args()


def generate_documentation(package_name: str, output_dir: Path, exclude_private: bool) -> int:
    """Generate Markdown documentation for the specified package.

    Args:
        package_name (str): Name of the package to document
        output_dir (Path): Directory to store the generated documentation
        exclude_private (bool): Whether to exclude private classes and methods

    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    try:
        package_to_markdown_structure(
            package_name,
            output_dir,
            exclude_private=exclude_private,
        )
    except (ImportError, ValueError, AttributeError):
        logger.exception("Error generating documentation")
        return 1
    else:
        logger.info(f"Documentation generated in {output_dir}")
        return 0


def main() -> int:
    """Run the CLI application.

    Returns:
        int: Exit code
    """
    args = parse_arguments()

    # Setup logging
    setup_logging(args.verbose)

    # Debug the package structure if requested
    if args.debug or args.verbose:
        debug_package_structure(args.package)

    # Generate documentation
    output_dir = Path(args.output_dir)
    return generate_documentation(args.package, output_dir, args.exclude_private)


if __name__ == "__main__":
    sys.exit(main())
