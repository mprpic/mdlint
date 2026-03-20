import re
from functools import cached_property
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

    _parser: MarkdownIt | None = None

    @classmethod
    def _get_parser(cls) -> MarkdownIt:
        if cls._parser is None:
            cls._parser = MarkdownIt().enable("table").use(front_matter_plugin)
        return cls._parser

    def __init__(self, path: Path, content: str) -> None:
        """Initialize document with path and content.

        Args:
            path: File path or Path("<stdin>") for stdin.
            content: Raw Markdown content.
        """
        self.path = path
        self.content = content
        self.lines = content.splitlines()

        self.tokens: list[Token] = self._get_parser().parse(content)

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

    @cached_property
    def code_block_lines(self) -> set[int]:
        """1-indexed line numbers inside fenced/indented code blocks."""
        code_lines: set[int] = set()
        for token in self.tokens:
            if token.type in ("fence", "code_block") and token.map:
                for line_num in range(token.map[0] + 1, token.map[1] + 1):
                    code_lines.add(line_num)
        return code_lines

    @cached_property
    def html_block_lines(self) -> set[int]:
        """1-indexed line numbers inside HTML blocks."""
        html_lines: set[int] = set()
        for token in self.tokens:
            if token.type == "html_block" and token.map:
                for line_num in range(token.map[0] + 1, token.map[1] + 1):
                    html_lines.add(line_num)
        return html_lines

    @cached_property
    def code_span_positions(self) -> dict[int, set[int]]:
        """Column positions inside inline code spans.

        Returns:
            Dict mapping 1-indexed line numbers to sets of 1-indexed column
            positions that are inside inline code spans.
        """
        code_columns: dict[int, set[int]] = {}
        for token in self.tokens:
            if token.type != "inline" or not token.map or not token.children:
                continue
            for line_num in range(token.map[0] + 1, token.map[1] + 1):
                line = self.get_line(line_num)
                if not line:
                    continue
                search_start = 0
                for child in token.children:
                    if child.type != "code_inline":
                        continue
                    full_span = child.markup + child.content + child.markup
                    idx = line.find(full_span, search_start)
                    if idx >= 0:
                        cols = code_columns.setdefault(line_num, set())
                        for col in range(idx + 1, idx + len(full_span) + 1):
                            cols.add(col)
                        search_start = idx + len(full_span)
        return code_columns

    # Pattern to match reference definitions: [ref]: destination [optional title]
    REFERENCE_DEF_PATTERN = re.compile(
        r"^\s*\[([^\]]+)\]:\s*"
        r"([^\s\"'(]+|<[^>]*>)"  # destination (bare or angle-bracketed)
        r"(?:\s+[\"'(].*)?\s*$"  # optional title
    )

    @cached_property
    def reference_definitions(self) -> dict[str, str]:
        """Reference definitions mapping lowercase IDs to destinations."""
        definitions: dict[str, str] = {}
        for line in self.lines:
            match = self.REFERENCE_DEF_PATTERN.match(line)
            if match:
                ref_id = match.group(1).lower()
                destination = match.group(2).strip()
                definitions[ref_id] = destination
        return definitions
