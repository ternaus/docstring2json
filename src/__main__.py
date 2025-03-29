"""Main entry point for TSX docstring converter."""

import argparse
import logging
from dataclasses import dataclass
from pathlib import Path

from docstring_2tsx.converter import file_to_tsx
from utils.shared import PackageConfig, package_to_structure

logger = logging.getLogger(__name__)


@dataclass
class DocumentationConfig:
    """Configuration for generating documentation."""

    package_name: str
    output_dir: Path
    exclude_private: bool = False


def generate_documentation(config: DocumentationConfig) -> None:
    """Generate documentation for a package.

    Args:
        config: Configuration for generating documentation
    """
    try:
        package_config = PackageConfig(
            package_name=config.package_name,
            output_dir=config.output_dir,
            exclude_private=config.exclude_private,
            converter_func=file_to_tsx,
            output_extension=".tsx",
            progress_desc="Generating TSX",
        )
        package_to_structure(package_config)
    except Exception:
        logger.exception("Error generating documentation")
        raise


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate TSX documentation from docstrings")
    parser.add_argument("--package-name", required=True, help="Name of the package to document")
    parser.add_argument("--output-dir", required=True, help="Directory to write documentation to")
    parser.add_argument("--exclude-private", action="store_true", help="Exclude private classes and methods")
    parser.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(level=getattr(logging, args.log_level.upper()))

    config = DocumentationConfig(
        package_name=args.package_name,
        output_dir=Path(args.output_dir),
        exclude_private=args.exclude_private,
    )
    generate_documentation(config)


if __name__ == "__main__":
    main()
