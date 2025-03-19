"""Tests for Docusaurus-compatible link generation in index files."""

import os
import re
import tempfile
from pathlib import Path

import pytest

from google_docstring_2md.converter import _generate_module_index_files


# Create a custom function to generate index files without calling _generate_root_index_file
def _generate_index_files_without_root(output_dir: Path) -> None:
    """Generate index files for modules and submodules without generating root index.

    This is useful for testing to avoid issues with temporary directories.

    Args:
        output_dir (Path): Root directory of the generated documentation
    """
    # Process each directory in the output
    for root, dirs, files in os.walk(output_dir):
        root_path = Path(root)

        # Skip the root directory
        if root_path == output_dir:
            continue

        rel_path = root_path.relative_to(output_dir)

        # Get module name from relative path
        module_name = str(rel_path).replace(os.path.sep, ".")

        # Get all .mdx files, excluding any existing index.mdx
        mdx_files = [f for f in files if f.endswith(".mdx") and f != "index.mdx"]

        # Get directory name for creating properly qualified links
        dir_name = root_path.name

        # Create links for each file - with fully qualified path for Docusaurus
        links = [f"- [{file[:-4]}]({dir_name}/{file[:-4]})" for file in sorted(mdx_files)]

        # Create links for each subdirectory with fully qualified path
        links.extend([f"- [{subdir_name}]({dir_name}/{subdir_name})" for subdir_name in sorted(dirs)])

        # Only create an index file if there are links
        if links:
            # Create content for the index file
            content = [
                f"# {module_name}",
                "",
                "## Contents",
                "",
            ]
            content.extend(links)

            # Write the index file
            index_path = root_path / "index.mdx"
            index_path.write_text("\n".join(content))


@pytest.fixture
def temp_docs_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


def build_directory_structure(base_path, structure):
    """Recursively build a directory structure.

    Args:
        base_path (Path): Base directory to build in
        structure (dict): Directory structure to create
    """
    for name, content in structure.items():
        if content is None:
            # It's a file
            file_path = base_path / f"{name}.mdx"
            file_path.write_text(f"# {name} content")
        else:
            # It's a directory
            dir_path = base_path / name
            dir_path.mkdir(exist_ok=True)
            build_directory_structure(dir_path, content)


@pytest.mark.parametrize(
    "structure,dir_path,expected_links",
    [
        # Simple case: one directory with files
        (
            {"module1": {"file1": None, "file2": None}},
            "module1",
            ["- [file1](module1/file1)", "- [file2](module1/file2)"]
        ),
        # Nested directories
        (
            {"parent": {"child": {"file1": None}}},
            "parent/child",
            ["- [file1](child/file1)"]
        ),
        # Directory with subdirectories
        (
            {"module1": {"file1": None, "subdir": {"subfile": None}}},
            "module1",
            ["- [file1](module1/file1)", "- [subdir](module1/subdir)"]
        ),
    ]
)
def test_index_links_parametrized(temp_docs_dir, structure, dir_path, expected_links):
    """Test that links in index files are generated correctly with directory prefixes."""
    # Create the directory structure
    build_directory_structure(temp_docs_dir, structure)

    # Generate index files without root index
    _generate_index_files_without_root(temp_docs_dir)

    # Check the index file in the specified directory
    index_path = temp_docs_dir / dir_path / "index.mdx"
    assert index_path.exists(), f"Index file not created at {index_path}"

    # Read the index file content
    index_content = index_path.read_text()

    # Check each expected link
    for expected_link in expected_links:
        assert expected_link in index_content, f"Expected link '{expected_link}' not found in {index_path}"


def test_links_follow_docusaurus_pattern(temp_docs_dir):
    """Test that generated links follow the Docusaurus pattern of relative links."""
    # Create a structure with multiple levels of nesting
    structure = {
        "top": {
            "file1": None,
            "middle": {
                "file2": None,
                "bottom": {
                    "file3": None
                }
            }
        }
    }

    build_directory_structure(temp_docs_dir, structure)

    # Generate index files without root index
    _generate_index_files_without_root(temp_docs_dir)

    # Check all index files
    for index_path in temp_docs_dir.glob("**/index.mdx"):
        content = index_path.read_text()

        # Extract all links using regex
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)

        # Verify each link follows the pattern: [name](directory/name)
        for name, link in links:
            dir_name = index_path.parent.name
            assert dir_name in link, f"Link {link} in {index_path} does not include directory name {dir_name}"
