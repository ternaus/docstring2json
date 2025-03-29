"""CLI for converting Python files to TSX documentation components."""

import argparse
from pathlib import Path

from docstring_2tsx.converter import package_to_tsx_files
from docstring_2tsx.utils.importer import import_module_from_file


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="Convert Python files to TSX documentation components")
    parser.add_argument("input_file", type=Path, help="Python file to convert")
    parser.add_argument("output_dir", type=Path, help="Directory to write TSX files")
    parser.add_argument("--github-repo", help="Base URL of the GitHub repository")
    parser.add_argument("--branch", default="main", help="Branch name for GitHub links")

    args = parser.parse_args()

    # Import the module
    module = import_module_from_file(args.input_file)

    # Convert to TSX files
    package_to_tsx_files(
        module,
        args.output_dir,
        github_repo=args.github_repo,
        branch=args.branch,
    )


if __name__ == "__main__":
    main()
