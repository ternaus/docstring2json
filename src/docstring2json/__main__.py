"""Main entry point for the docstring to JSON converter."""

import argparse
import logging
import sys
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Smart import that works both for direct script execution and installed package
try:
    # First, try relative import (when installed as package)
    from docstring2json.converter import file_to_json
    from docstring2json.utils.shared import process_package
except ImportError:
    # If that fails, try with src prefix (when running as script)
    try:
        from src.docstring2json.converter import file_to_json
        from src.docstring2json.utils.shared import process_package
    except ImportError:
        # Last resort - add src to path
        src_dir = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(src_dir))
        from src.docstring2json.converter import file_to_json
        from src.docstring2json.utils.shared import process_package


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Convert Python docstrings to JSON")
    parser.add_argument("--package-name", required=True, help="Name of the package to process")
    parser.add_argument("--output-dir", required=True, help="Directory to write output files")
    parser.add_argument("--exclude-private", action="store_true", help="Exclude private members")
    args = parser.parse_args()

    process_package(
        package_name=args.package_name,
        output_dir=Path(args.output_dir),
        converter_func=file_to_json,
        exclude_private=args.exclude_private,
    )


if __name__ == "__main__":
    main()
