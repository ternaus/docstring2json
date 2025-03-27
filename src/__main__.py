"""Main entry point for docstring converters."""

import argparse
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from docstring_2md.converter import file_to_markdown
from docstring_2tsx.converter import file_to_tsx
from utils.shared import PackageConfig, package_to_structure

logger = logging.getLogger(__name__)


class FileFormat(str, Enum):
    """Supported file formats."""

    MDX = "mdx"
    TSX = "tsx"


FORMAT_CONFIG = {
    FileFormat.MDX: {
        "converter": file_to_markdown,
        "extension": ".mdx",
        "desc": "Generating markdown",
    },
    FileFormat.TSX: {
        "converter": file_to_tsx,
        "extension": ".tsx",
        "desc": "Generating TSX",
    },
}


@dataclass
class DocumentationConfig:
    """Configuration for generating documentation."""

    package_name: str
    output_dir: Path
    file_format: FileFormat
    exclude_private: bool = False
    github_repo: str | None = None
    branch: str = "main"


def generate_documentation(config: DocumentationConfig) -> None:
    """Generate documentation for a package.

    Args:
        config: Configuration for generating documentation
    """
    try:
        format_settings = FORMAT_CONFIG[config.file_format]
        package_config = PackageConfig(
            package_name=config.package_name,
            output_dir=config.output_dir,
            exclude_private=config.exclude_private,
            github_repo=config.github_repo,
            branch=config.branch,
            converter_func=format_settings["converter"],
            output_extension=format_settings["extension"],
            progress_desc=format_settings["desc"],
        )
        package_to_structure(package_config)
    except Exception:
        logger.exception("Error generating documentation")
        raise


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate documentation from docstrings")
    parser.add_argument("--package-name", required=True, help="Name of the package to document")
    parser.add_argument("--output-dir", required=True, help="Directory to write documentation to")
    parser.add_argument(
        "--format",
        type=FileFormat,
        choices=list(FileFormat),
        default=FileFormat.MDX,
        help="Output file format (mdx or tsx)",
    )
    parser.add_argument("--exclude-private", action="store_true", help="Exclude private classes and methods")
    parser.add_argument("--github-repo", help="Base URL of the GitHub repository")
    parser.add_argument("--branch", default="main", help="Branch name to link to")

    args = parser.parse_args()

    config = DocumentationConfig(
        package_name=args.package_name,
        output_dir=Path(args.output_dir),
        file_format=args.format,
        exclude_private=args.exclude_private,
        github_repo=args.github_repo,
        branch=args.branch,
    )
    generate_documentation(config)


if __name__ == "__main__":
    main()
