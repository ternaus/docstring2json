"""Main entry point for the docstring to TSX converter."""

import argparse
import logging
import sys
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_dir))

from docstring_2tsx.converter import file_to_tsx

from utils.shared import process_package

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Add src directory to Python path
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Convert Python docstrings to TSX")
    parser.add_argument("--package-name", required=True, help="Name of the package to process")
    parser.add_argument("--output-dir", required=True, help="Directory to write output files")
    parser.add_argument("--exclude-private", action="store_true", help="Exclude private members")
    args = parser.parse_args()

    process_package(
        package_name=args.package_name,
        output_dir=Path(args.output_dir),
        converter_func=file_to_tsx,
        exclude_private=args.exclude_private,
    )


if __name__ == "__main__":
    main()
