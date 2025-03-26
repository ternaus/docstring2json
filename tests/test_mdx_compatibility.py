"""Tests for MDX compatibility in the generated markdown."""

import pytest

from src.docstring_2md.converter import class_to_markdown
from src.docstring_2md.processor import (
    escape_mdx_special_chars,
    extract_param_docs,
    format_section_content,
)
from src.utils.signature_formatter import Parameter


@pytest.mark.parametrize(
    "input_text, expected_output",
    [
        ("text with <angle> brackets", "text with \\<angle\\> brackets"),
        ("param=value", "param\\=value"),
        ("normal text", "normal text"),
        ("multiple <= signs =>", "multiple \\<\\= signs \\=\\>"),
        ("", ""),
        (None, None),
    ],
)
def test_escape_mdx_special_chars(input_text, expected_output):
    """Test that MDX special characters are properly escaped."""
    result = escape_mdx_special_chars(input_text)
    assert result == expected_output


@pytest.mark.parametrize(
    "section, content, expected_output_contains",
    [
        ("Examples", ">>> a = 1\n>>> print(a)", "```python"),
        ("Returns", "[{'type': 'dict<str, any>', 'desc': 'some info'}]", "```\n["),
        ("Notes", "This is a note with <special> chars", "```\nThis is a note"),
    ],
)
def test_format_section_content(section, content, expected_output_contains):
    """Test that section content is properly formatted for MDX."""
    result = format_section_content(section, content)
    assert expected_output_contains in result
    assert "PreserveFormat" not in result


# Sample class used for testing, not a test class itself
class DocTestClass:
    """Test class with special characters in docstring.

    This class has <angle brackets> and param=value in its description.

    Args:
        param1 (str): Description with <angle> brackets
        param2 (int): Description with param=value

    Returns:
        dict<str, any>: A dictionary with special chars
    """

    def __init__(self, param1: str, param2: int = 5):
        self.param1 = param1
        self.param2 = param2


def test_class_to_markdown_with_special_chars():
    """Test that class_to_markdown properly handles special characters."""
    result = class_to_markdown(DocTestClass)

    # Description should be escaped
    assert "\\<angle brackets\\>" in result
    assert "param\\=value" in result

    # For parameters, we only check that they appear somewhere in the output
    # We don't check exact formatting since that may change with our HTML/pre tag approach
    assert "param1" in result
    assert "param2" in result
    assert "Description with" in result
    assert "angle" in result
    assert "brackets" in result


@pytest.mark.parametrize(
    "param_name, param_type, param_default, param_desc, expected_type, expected_desc",
    [
        (
            "normal_param", "str", None, "Normal description",
            "str", "Normal description"
        ),
        (
            "special_param", "dict<str, any>", None, "Description with <angle> brackets",
            "dict\\<str, any\\>", "Description with <angle> brackets"
        ),
        (
            "equals_param", "str", None, "Description with param=value",
            "str", "Description with param=value"
        ),
    ],
)
def test_extract_param_docs_escaping(
    param_name, param_type, param_default, param_desc, expected_type, expected_desc
):
    """Test that _extract_param_docs properly escapes special characters."""
    param = Parameter(name=param_name, type=param_type, default=param_default)
    param_docs = {param_name: {"description": param_desc, "type": param_type}}

    # Create a simple object for testing
    class TestObj:
        __annotations__ = {}

    doc_type, desc = extract_param_docs(param, param_docs, TestObj)

    assert doc_type == expected_type
    assert desc == expected_desc
