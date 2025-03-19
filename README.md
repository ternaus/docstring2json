# google-docstring-2md

Generate markdown documentation from Python packages with Google-style docstrings.

## Installation

```bash
pip install google-docstring-2md
```

## Usage

### Command-line Interface

The simplest way to use google-docstring-2md is through the command-line interface:

```bash
# Generate documentation for a package
docstring2md albumentations -o ./albumentations_docs

# Exclude private classes and methods
docstring2md pandas --exclude-private -o ./pandas_docs
```

### Python API

You can also use the package programmatically:

```python
from pathlib import Path
from google_docstring_2md import class_to_markdown, file_to_markdown, package_to_markdown_structure

# Document a single class
from some_module import SomeClass
markdown = class_to_markdown(SomeClass)
print(markdown)

# Document a module and save to a file
import some_module
markdown = file_to_markdown(some_module, "some_module")
Path("some_module.md").write_text(markdown)

# Document an entire package
output_dir = Path("./docs")
package_to_markdown_structure("numpy", output_dir, exclude_private=True)
```

### Output Directory Structure

The output directory will have a structure that mirrors the package structure, but simplifies it:

```
output_dir/
├── module1.md       # Contains all classes and functions from module1.py
├── submodule/       # Folder from package.submodule
│   ├── module2.md   # Contains all classes and functions from package.submodule.module2
```

Each markdown file includes:
1. A heading with the module name
2. A table of contents
3. Sections for classes and functions
4. Code examples preserved from docstrings

## Features

- Preserves package structure in generated documentation
- Creates markdown files for each class
- Formats docstring sections (Args, Returns, Examples, etc.)
- Properly formats code examples from docstrings
- Generates parameter tables with types and descriptions
- Supports all Google-style docstring sections
- Adds GitHub source links when a GitHub repository is specified

## GitHub Source Links

When generating documentation, you can provide a GitHub repository URL to add "View source on GitHub" links:

```python
# Add GitHub source links to the documentation
package_to_markdown_structure("your_package", output_dir, github_repo="https://github.com/username/repository")
```

### Styling GitHub Links in Docusaurus

The GitHub links are added with specific class names that can be styled in your Docusaurus project:

1. Add custom CSS to your Docusaurus site by creating or editing `src/css/custom.css`:

```css
/* GitHub source link styling */
.github-source-container {
  display: flex;
  align-items: center;
  background-color: #f6f8fa;
  border: 1px solid #ddd;
  border-radius: 6px;
  padding: 8px 16px;
  margin-bottom: 24px;
  transition: background-color 0.2s;
}

.github-source-container:hover {
  background-color: #ebedf0;
}

.github-icon {
  display: flex;
  margin-right: 8px;
}

.github-source-link {
  color: #0366d6 !important;
  font-weight: 500;
  text-decoration: none;
}

.github-source-link:hover {
  text-decoration: underline;
}
```

2. Make sure your custom CSS is imported in your Docusaurus configuration:

```js
// docusaurus.config.js
module.exports = {
  // ...
  presets: [
    [
      '@docusaurus/preset-classic',
      {
        // ...
        theme: {
          customCss: [require.resolve('./src/css/custom.css')],
        },
      },
    ],
  ],
};
```

This will create visually distinct GitHub source links in your documentation.

## Example Output

For a class like:

```python
class ElasticTransform:
    """Apply elastic deformation to images, masks, bounding boxes, and keypoints.

    This transformation introduces random elastic distortions to the input data. It's particularly
    useful for data augmentation in training deep learning models, especially for tasks like
    image segmentation or object detection where you want to maintain the relative positions of
    features while introducing realistic deformations.

    Args:
        alpha (float): Scaling factor for the random displacement fields. Higher values result in
            more pronounced distortions. Default: 1.0
        sigma (float): Standard deviation of the Gaussian filter used to smooth the displacement
            fields. Higher values result in smoother, more global distortions. Default: 50.0

    Example:
        >>> import albumentations as A
        >>> transform = A.ElasticTransform(alpha=1, sigma=50, p=0.5)
    """
```

The generated markdown will look like:

```markdown
# ElasticTransform
```python
ElasticTransform(alpha=1.0, sigma=50.0, p=0.5)
```

Apply elastic deformation to images, masks, bounding boxes, and keypoints.

This transformation introduces random elastic distortions to the input data. It's particularly
useful for data augmentation in training deep learning models, especially for tasks like
image segmentation or object detection where you want to maintain the relative positions of
features while introducing realistic deformations.

## Parameters
| Name | Type | Description |
|------|------|-------------|
| alpha | float | Scaling factor for the random displacement fields. Higher values result in more pronounced distortions. Default: 1.0 |
| sigma | float | Standard deviation of the Gaussian filter used to smooth the displacement fields. Higher values result in smoother, more global distortions. Default: 50.0 |

## Example
```python
import albumentations as A
transform = A.ElasticTransform(alpha=1, sigma=50, p=0.5)
```
```

## Requirements

- Python 3.10+
- `docstring-parser` for docstring parsing
- `tqdm` for progress reporting

## License

Custom License - See LICENSE file for details
