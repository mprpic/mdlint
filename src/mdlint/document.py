from pathlib import Path

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdit_py_plugins.front_matter import front_matter_plugin


class Document:
    """A parsed Markdown file.

    Attributes:
        path: File path (or Path("<stdin>") for stdin input).
        content: Raw file content.
        tokens: Parsed markdown-it-py tokens.
        lines: Content split by lines for source analysis.
        front_matter: Extracted front matter content if present.
    """

    def __init__(self, path: Path, content: str) -> None:
        """Initialize document with path and content.

        Args:
            path: File path or Path("<stdin>") for stdin.
            content: Raw Markdown content.
        """
        self.path = path
        self.content = content
        self.lines = content.splitlines()

        # Parse with front matter and table support
        md = MarkdownIt().enable("table").use(front_matter_plugin)
        self.tokens: list[Token] = md.parse(content)

        # Extract front matter if present
        self.front_matter: str | None = None
        for token in self.tokens:
            if token.type == "front_matter":
                self.front_matter = token.content
                break

    def get_line(self, line_number: int) -> str | None:
        """Get line content by 1-indexed line number.

        Args:
            line_number: 1-indexed line number.

        Returns:
            Line content or None if out of range.
        """
        if 1 <= line_number <= len(self.lines):
            return self.lines[line_number - 1]
        return None
