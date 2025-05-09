# Google Docstring to JSON Converter

A tool that converts Python package docstrings to JSON files.

## License

This software is licensed under a custom license agreement. The Albumentations Team and their official contributors have free access to use this software for their projects. All other users must obtain a paid license.

For licensing inquiries, please contact:
Vladimir Iglovikov (iglovikov@gmail.com)

See the [LICENSE](LICENSE) file for full details.

## Features

- Converts Google-style docstrings to JSON format
- Maintains the original package structure in the output
- Supports both class and function documentation
- Handles module-level docstrings
- Preserves code examples and formatting
- Supports complex type definitions with interactive display

## Installation

```bash
pip install docstring2json
```

## Usage

```bash
python -m src.docstring2json.__main__ --package-name PACKAGE_NAME --output-dir OUTPUT_DIR
```

or:
```bash
docstring2json --package-name PACKAGE_NAME --output-dir OUTPUT_DIR
```

This will:
1. Import the specified package
2. Extract docstrings from all classes, functions, and modules
3. Write JSON files for each module with proper routing

## Output Structure

The tool creates a directory structure that matches the input package:

```
output_dir/
  module1/
    file1/
      data.json
    file2/
      data.json
  module2/
    submodule/
      file2/
        data.json
```

Each `data.json` file contains:
- Module name and description
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
