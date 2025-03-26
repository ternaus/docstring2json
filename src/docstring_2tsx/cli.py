"""CLI for converting Python files to TSX documentation components."""

import argparse
import inspect
import logging
from pathlib import Path

from docstring_2tsx.converter import class_to_tsx
from docstring_2tsx.utils.importer import import_from_file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="Convert Python files to TSX documentation components")
    parser.add_argument("input_file", type=str, help="Input Python file")
    parser.add_argument("output_dir", type=str, help="Output directory for TSX files")
    parser.add_argument("--github-repo", type=str, help="GitHub repository URL")
    parser.add_argument("--branch", type=str, default="main", help="GitHub branch name")

    args = parser.parse_args()

    # Create output directory if it doesn't exist
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Import the Python module
    module = import_from_file(args.input_file)

    # Convert each class and function to TSX
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) or inspect.isfunction(obj):
            tsx_content = class_to_tsx(obj, github_repo=args.github_repo, branch=args.branch)
            output_file = output_dir / f"{name}.tsx"
            output_file.write_text(tsx_content)
            logger.info(f"Converted {name} to {output_file}")


if __name__ == "__main__":
    main()
