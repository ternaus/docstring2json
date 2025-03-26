"""Main entry point for docstring_2md."""

import argparse
import logging
from pathlib import Path

from google_docstring_2md.converter import file_to_markdown

from utils.shared import PackageConfig, package_to_structure

logger = logging.getLogger(__name__)


def generate_documentation(
    package_name: str,
    output_dir: Path,
    *,
    exclude_private: bool = False,
    github_repo: str | None = None,
    branch: str = "main",
) -> None:
    """Generate markdown documentation for a package.

    Args:
        package_name: Name of the package to document
        output_dir: Directory to write documentation to
        exclude_private: Whether to exclude private classes and methods
        github_repo: Base URL of the GitHub repository
        branch: Branch name to link to
    """
    try:
        config = PackageConfig(
            package_name=package_name,
            output_dir=output_dir,
            exclude_private=exclude_private,
            github_repo=github_repo,
            branch=branch,
            converter_func=file_to_markdown,
            output_extension=".mdx",
            progress_desc="Generating markdown",
        )
        package_to_structure(config)
    except Exception:
        logger.exception("Error generating documentation")
        raise


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate markdown documentation from docstrings")
    parser.add_argument("package_name", help="Name of the package to document")
    parser.add_argument("output_dir", help="Directory to write documentation to")
    parser.add_argument("--exclude-private", action="store_true", help="Exclude private classes and methods")
    parser.add_argument("--github-repo", help="Base URL of the GitHub repository")
    parser.add_argument("--branch", default="main", help="Branch name to link to")

    args = parser.parse_args()

    generate_documentation(
        package_name=args.package_name,
        output_dir=Path(args.output_dir),
        exclude_private=args.exclude_private,
        github_repo=args.github_repo,
        branch=args.branch,
    )


if __name__ == "__main__":
    main()
