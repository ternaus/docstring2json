"""TSX component templates.

This module provides templates for TSX components used in documentation.
"""

from utils.signature_formatter import Parameter


def parameter_table_template(params: list[Parameter]) -> str:
    """Generate TSX template for parameter table.

    Args:
        params (list[Parameter]): List of parameters to document

    Returns:
        str: TSX template for parameter table
    """
    if not params:
        return ""

    return """
    <table>
        <thead>
            <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Description</th>
            </tr>
        </thead>
        <tbody>
            {params.map((param) => (
                <tr key={param.name}>
                    <td>{param.name}</td>
                    <td>{param.type}</td>
                    <td>{param.description}</td>
                </tr>
            ))}
        </tbody>
    </table>
    """


def code_block_template(code: str, language: str = "python") -> str:
    """Generate TSX template for code block.

    Args:
        code (str): Code to display
        language (str): Programming language for syntax highlighting

    Returns:
        str: TSX template for code block
    """
    return f"""
    <pre>
        <code className="language-{language}">
            {code}
        </code>
    </pre>
    """
