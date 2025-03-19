"""Tests for module index file generation."""

import os
import tempfile
from pathlib import Path

import pytest

from google_docstring_2md.converter import _generate_module_index_files, _generate_root_index_file


@pytest.fixture
def mock_docs_structure():
    """Create a temporary directory with a mock documentation structure."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create a module directory structure
        module1 = temp_path / "module1"
        module1.mkdir()

        # Create files in module1
        (module1 / "file1.mdx").write_text("# File1 content")
        (module1 / "file2.mdx").write_text("# File2 content")

        # Create a submodule
        submodule = module1 / "submodule"
        submodule.mkdir()

        # Create files in submodule
        (submodule / "subfile1.mdx").write_text("# Subfile1 content")

        # Create another module at root
        module2 = temp_path / "module2"
        module2.mkdir()
        (module2 / "otherfile.mdx").write_text("# Otherfile content")

        # Create a root file
        (temp_path / "root_file.mdx").write_text("# Root file content")

        yield temp_path


def test_generate_module_index_files(mock_docs_structure):
    """Test that module index files are generated correctly with proper relative links."""
    # Generate index files
    _generate_module_index_files(mock_docs_structure)

    # Check that index files exist
    assert (mock_docs_structure / "module1" / "index.mdx").exists()
    assert (mock_docs_structure / "module1" / "submodule" / "index.mdx").exists()
    assert (mock_docs_structure / "module2" / "index.mdx").exists()
    assert (mock_docs_structure / "index.mdx").exists()

    # Check content of module1 index
    module1_index = (mock_docs_structure / "module1" / "index.mdx").read_text()
    assert "# module1" in module1_index
    assert "- [file1](module1/file1)" in module1_index
    assert "- [file2](module1/file2)" in module1_index
    assert "- [submodule](module1/submodule)" in module1_index

    # Check content of submodule index
    submodule_index = (mock_docs_structure / "module1" / "submodule" / "index.mdx").read_text()
    assert "# module1.submodule" in submodule_index
    assert "- [subfile1](submodule/subfile1)" in submodule_index

    # Check content of root index
    root_index = (mock_docs_structure / "index.mdx").read_text()
    assert "# API Documentation" in root_index
    assert "- [module1](module1)" in root_index
    assert "- [module2](module2)" in root_index
    assert "- [root_file](root_file)" in root_index


def test_generate_root_index_file(mock_docs_structure):
    """Test that the root index file is generated correctly."""
    # Generate only the root index file
    _generate_root_index_file(mock_docs_structure)

    # Check that the root index file exists
    assert (mock_docs_structure / "index.mdx").exists()

    # Check content
    root_index = (mock_docs_structure / "index.mdx").read_text()
    assert "# API Documentation" in root_index
    assert "## Modules" in root_index
    assert "- [module1](module1)" in root_index
    assert "- [module2](module2)" in root_index
    assert "- [root_file](root_file)" in root_index
