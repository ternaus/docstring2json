# Google Docstring to TSX/MDX Converter

A tool that converts Python package docstrings to TSX or MDX files for Next.js documentation.

## Features

- Converts Google-style docstrings to TSX/MDX format
- Preserves type information and parameter descriptions
- Maintains the original package structure in the output
- Generates source code and line numbers for each class/function
- Supports both class and function documentation

## Installation

```bash
pip install google-docstring-2md
```

## Usage

```bash
python -m src.docstring_2tsx package_name output_dir
```

For example:
```bash
python -m src.docstring_2tsx albumentations docs
```

This will:
1. Import the specified package
2. Extract docstrings from all classes and functions
3. Convert them to TSX format
4. Create a directory structure matching the package
5. Write TSX files for each module

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
- Module name and description
- List of classes and functions
- Source code and line numbers
- Parameter descriptions and types
- Return values and exceptions

## Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run pre-commit hooks
pre-commit run --all-files
```

## License

MIT
