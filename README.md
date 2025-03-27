# A tool to convert Google-style docstrings to TSX format

> [!IMPORTANT]
> This package requires a PAID LICENSE for all users EXCEPT the Albumentations Team.
> Contact iglovikov@gmail.com to obtain a license before using this software.

A Python package for parsing Google-style docstrings into structured dictionaries.

## License Information

This package is available under a custom license:
- **Free for Albumentations Team projects** (https://github.com/albumentations-team)
- **Paid license required for all other users** (individuals, companies, and other open-source projects)

See the [LICENSE](LICENSE) file for complete details.

## Installation

```bash
pip install google-docstring-2tsx
```

## Usage

### Command-line Interface

The simplest way to use google-docstring-2tsx is through the command-line interface:

```bash
# Generate TSX documentation for a package
docstring2tsx albumentations -o ./albumentations_docs

# Exclude private classes and methods
docstring2tsx pandas --exclude-private -o ./pandas_docs

# Generate docs with GitHub source links
docstring2tsx albumentations -o ./docusaurus-test/docs --github-repo https://github.com/albumentations-team/albumentations
```

### Python API

You can also use the package programmatically:

```python
from pathlib import Path
from google_docstring_2tsx import class_to_tsx, file_to_tsx, package_to_tsx_structure

# Document a single class
from some_module import SomeClass
tsx_content = class_to_tsx(SomeClass)
print(tsx_content)

# Document a module and save to a file
import some_module
tsx_content = file_to_tsx(some_module, "some_module")
Path("some_module.page.tsx").write_text(tsx_content)

# Document an entire package
output_dir = Path("./docs")
package_to_tsx_structure("numpy", output_dir, exclude_private=True)
```

### Output Directory Structure

The output directory will have a structure that mirrors the package structure:

```
output_dir/
├── module1/
│   └── page.tsx     # Contains docs for classes/functions from module1.py
├── submodule/
│   ├── module2/
│   │   └── page.tsx # Contains docs for classes/functions from package.submodule.module2
```

Each `page.tsx` file includes:
1. Imports for necessary components (future)
2. Structured data derived from docstrings
3. JSX rendering components (future) for signature, descriptions, parameters, examples, etc.

## Features

- Preserves package structure in generated documentation folders
- Creates `page.tsx` files for each module, suitable for Next.js app router
- Parses docstring sections (Args, Returns, Examples, etc.) into structured data
- Properly formats code examples from docstrings
- Generates parameter tables (via components, future)
- Supports all Google-style docstring sections
- Adds GitHub source links when a GitHub repository is specified

## GitHub Source Links

When generating documentation, you can provide a GitHub repository URL to add "View source on GitHub" links:

```python
# Add GitHub source links to the documentation
package_to_tsx_structure("your_package", output_dir, github_repo="https://github.com/username/repository")
```

### Styling GitHub Links (Future - Component Based)

Styling will be handled directly within the TSX components using standard React/Next.js styling methods (e.g., CSS Modules, Tailwind CSS).

## Example Output (Future - Component Based)

The generated `page.tsx` will import and use components to render the documentation based on parsed data.

## Requirements

- Python 3.10+
- `docstring-parser` for docstring parsing
- `tqdm` for progress reporting

## License

Custom License - See LICENSE file for details
