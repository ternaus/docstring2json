"""Command-line interface for google-docstring-2md.

This module provides a command-line interface to convert Google-style docstrings to Markdown.
"""

import argparse
import logging
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


def main() -> int:
    """Run the CLI application.

    Returns:
        int: Exit code
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

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    try:
        # Convert the package
        output_dir = Path(args.output_dir)
        package_to_markdown_structure(
            args.package,
            output_dir,
            exclude_private=args.exclude_private,
        )
    except Exception:
        logger.exception("Error generating documentation")
        return 1
    else:
        logger.info(f"Documentation generated in {output_dir}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
