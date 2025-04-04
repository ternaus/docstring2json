# Google Docstring to TSX Converter

A tool that converts Python package docstrings to TSX files for Next.js documentation, with a focus on generating beautiful, interactive documentation.

## License

This software is licensed under a custom license agreement. The Albumentations Team and their official contributors have free access to use this software for their projects. All other users must obtain a paid license.

For licensing inquiries, please contact:
Vladimir Iglovikov (iglovikov@gmail.com)

See the [LICENSE](LICENSE) file for full details.

## Features

- Converts Google-style docstrings to TSX format with modern UI components
- Preserves type information and parameter descriptions with syntax highlighting
- Maintains the original package structure in the output
- Generates source code with toggle functionality for each class/function
- Supports both class and function documentation
- Creates a table of contents for easy navigation
- Handles module-level docstrings
- Preserves code examples and formatting
- Supports complex type definitions with interactive display
- Generates responsive, dark-themed documentation

## Installation

```bash
pip install docstring2tsx
```

## Usage

```bash
python -m src.docstring2tsx.__main__ --package-name PACKAGE_NAME --output-dir OUTPUT_DIR
```

or:
```bash
docstring2tsx --package-name PACKAGE_NAME --output-dir OUTPUT_DIR
```

This will:
1. Import the specified package
2. Extract docstrings from all classes, functions, and modules
3. Convert them to TSX format with modern UI components
4. Create a directory structure matching the package
5. Write TSX files for each module with proper routing

## Output Structure

The tool creates a directory structure that matches the input package:

```
output_dir/
  module1/
    page.tsx
  module2/
    submodule/
      page.tsx
```

Each `page.tsx` file contains:
- Module name and description in a styled container
- Table of contents with links to classes and functions
- Interactive source code display with toggle functionality
- Parameter descriptions with type information
- Return values and exceptions with proper formatting
- Code examples with syntax highlighting
- References and links to related documentation

## Development

```bash
# Install dependencies
pip install -e .

# Run tests
pytest

# Run pre-commit hooks
pre-commit run --all-files
```
