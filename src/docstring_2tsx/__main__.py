"""Command-line interface for google-docstring-2tsx.

This module provides a command-line interface to convert Google-style docstrings to TSX.
"""

import argparse
import importlib
import inspect
import logging
import pkgutil
import sys
from pathlib import Path

from .converter import class_to_tsx

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
        package_logger = logging.getLogger("docstring_2tsx")
        package_logger.setLevel(logging.DEBUG)

        # Add a stream handler if none exists
        if not package_logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            package_logger.addHandler(handler)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Convert Google-style docstrings to TSX documentation",
    )

    parser.add_argument(
        "package",
        help="Name of the package to document",
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        default="./docs",
        help="Output directory for TSX files (default: ./docs)",
    )

    parser.add_argument(
        "--exclude-private",
        action="store_true",
        help="Exclude private classes and methods (starting with _)",
    )

    parser.add_argument(
        "--github-repo",
        help="Base URL of the GitHub repository (e.g., 'https://github.com/username/repo') "
        "or path to a local git repository",
    )

    parser.add_argument(
        "--branch",
        default="main",
        help="The branch name to link to (default: 'main')",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser.parse_args()


def generate_documentation(
    package_name: str,
    output_dir: Path,
    exclude_private: bool,
    github_repo: str | None = None,
    branch: str = "main",
) -> int:
    """Generate TSX documentation for the specified package.

    Args:
        package_name (str): Name of the package to document
        output_dir (Path): Directory to store the generated documentation
        exclude_private (bool): Whether to exclude private classes and methods
        github_repo (str | None): Base URL of the GitHub repository or path to a local git repository
        branch (str): The branch name to link to (default: "main")

    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    try:
        # Import the package
        package = importlib.import_module(package_name)
        output_dir.mkdir(exist_ok=True, parents=True)

        # Process all classes and functions in the package
        for name, obj in pkgutil.iter_modules(package.__path__):
            # Skip private members if exclude_private is True
            if exclude_private and name.startswith("_"):
                continue

            # Only consider classes and functions defined in this module
            if (hasattr(obj, "__module__") and obj.__module__ == package.__name__) or (
                inspect.isclass(obj) or inspect.isfunction(obj)
            ):
                try:
                    tsx = class_to_tsx(obj, github_repo=github_repo, branch=branch)
                    output_file = output_dir / f"{name}.tsx"
                    output_file.write_text(tsx)
                except (ValueError, TypeError, AttributeError):
                    logger.exception("Error processing %s", name)

        logger.info(f"Documentation generated in {output_dir}")
        return 0

    except ImportError:
        logger.exception(f"Could not import package '{package_name}'")
        return 1
    except (ValueError, TypeError, AttributeError):
        logger.exception(f"Error processing package '{package_name}'")
        return 1


def main() -> int:
    """Run the CLI application.

    Returns:
        int: Exit code
    """
    args = parse_arguments()

    # Setup logging
    setup_logging(args.verbose)

    # Generate documentation
    output_dir = Path(args.output_dir)
    return generate_documentation(
        args.package,
        output_dir,
        args.exclude_private,
        args.github_repo,
        args.branch,
    )


if __name__ == "__main__":
    sys.exit(main())
