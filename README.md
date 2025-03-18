# google-docstring-2md

Generate markdown documentation from Python packages with Google-style docstrings.

## Installation

```bash
pip install google-docstring-2md
```

## Usage

```python
from pathlib import Path
from google_docstring_2md import class_to_markdown, package_to_markdown_structure

# Generate markdown for a single class
from albumentations import ElasticTransform
markdown = class_to_markdown(ElasticTransform)
print(markdown)

# Generate markdown files for an entire package
package_to_markdown_structure("albumentations", Path("./docs"))

# Generate markdown files excluding private members (starting with _)
package_to_markdown_structure("albumentations", Path("./docs"), exclude_private=True)
```

## Features

- Preserves package structure in generated documentation
- Creates markdown files for each class
- Formats docstring sections (Args, Returns, Examples, etc.)
- Properly formats code examples from docstrings
- Generates parameter tables with types and descriptions
- Supports all Google-style docstring sections

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
- `google-docstring-parser` for docstring parsing

## License

Custom License - See LICENSE file for details
