"""CLI for converting Python files to JSON documentation."""

import argparse
from pathlib import Path

from docstring2tsx.converter import file_to_json

from utils.importer import import_module_from_file
from utils.shared import process_package


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="Convert Python files to JSON documentation")
    parser.add_argument("input_file", type=Path, help="Python file to convert")
    parser.add_argument("output_dir", type=Path, help="Directory to write JSON files")
    parser.add_argument("--exclude-private", action="store_true", help="Exclude private members")

    args = parser.parse_args()

    # Import the module
    module = import_module_from_file(args.input_file)

    # Convert to JSON files
    process_package(
        package_name=module.__name__,
        output_dir=args.output_dir,
        converter_func=file_to_json,
        exclude_private=args.exclude_private,
    )


if __name__ == "__main__":
    main()
