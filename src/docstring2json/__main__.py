"""Main entry point for the docstring to JSON converter."""

import argparse
import logging
import sys
from pathlib import Path

# Add the project root directory to sys.path
src_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(src_dir))

# Add the src directory itself to sys.path
parent_dir = Path(__file__).parent.parent  # This is the src directory
sys.path.insert(0, str(parent_dir))

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

from docstring2json.converter import file_to_json
from docstring2json.utils.shared import process_package


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Convert Python docstrings to JSON")
    parser.add_argument("--package-name", required=True, help="Name of the package to process")
    parser.add_argument("--output-dir", required=True, help="Directory to write output files")
    parser.add_argument("--exclude-private", action="store_true", help="Exclude private members")
    args = parser.parse_args()

    # Call process_package with arguments as a dictionary
    process_package(
        package_name=args.package_name,
        output_dir=Path(args.output_dir),
        converter_func=file_to_json,
        exclude_private=args.exclude_private,
    )


if __name__ == "__main__":
    main()
