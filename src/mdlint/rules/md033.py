import re
from dataclasses import dataclass, field

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD033Config(RuleConfig):
    """Configuration for MD033 rule."""

    allowed_elements: list[str] = field(
        default_factory=list,
        metadata={
            "description": "List of HTML element names that are allowed.",
        },
    )
    table_allowed_elements: list[str] | None = field(
        default=None,
        metadata={
            "description": (
                "List of HTML element names allowed in tables. "
                "Falls back to allowed_elements if not set."
            ),
        },
    )


class MD033(Rule[MD033Config]):
    """Inline HTML."""

    id = "MD033"
    name = "no-inline-html"
    summary = "Inline HTML"
    config_class = MD033Config

    description = (
        "This rule detects the use of raw HTML elements within Markdown content. "
        "HTML elements in code blocks and HTML comments are not flagged."
    )

    rationale = (
        "Raw HTML in Markdown documents may not render correctly in all Markdown "
        "parsers and can cause issues when converting to non-HTML formats. Using "
        "native Markdown syntax ensures better portability and consistency."
    )

    example_valid = """\
# Valid Markdown

This is a paragraph with **bold** and *italic* text.

- List item one
- List item two

```html
<div>Code blocks are allowed</div>
```
"""

    example_invalid = """\
# Invalid Document

<div>This is inline HTML</div>

Some text with <span>inline HTML</span> inside.

<p>A paragraph using HTML</p>
"""

    # Pattern to match opening HTML tags (not closing tags)
    # Matches: <tag>, <tag attr="val">, <tag/>, <tag />
    # Does NOT match: </tag>, autolinks like <https://...> or <mailto:...>
    HTML_TAG_PATTERN = re.compile(
        r"<\s*([a-zA-Z][a-zA-Z0-9]*)(?=[\s/>])\s*[^>]*?>",
        re.IGNORECASE,
    )

    @staticmethod
    def _get_html_comment_positions(document: Document) -> dict[int, set[int]]:
        """Get positions inside HTML comments.

        Processes the full document content to correctly handle multi-line
        comments that span across lines.

        Returns:
            Dict mapping 1-indexed line numbers to sets of 1-indexed
            positions that are inside HTML comments.
        """
        comment_positions: dict[int, set[int]] = {}

        for match in re.finditer(r"<!--.*?-->", document.content, re.DOTALL):
            match_lines = match.group().split("\n")
            start_line = document.content[: match.start()].count("\n") + 1
            last_newline = document.content.rfind("\n", 0, match.start())
            start_col = match.start() - last_newline  # 1-indexed

            for i, mline in enumerate(match_lines):
                line_num = start_line + i
                cols = comment_positions.setdefault(line_num, set())
                if i == 0:
                    cols.update(range(start_col, start_col + len(mline)))
                else:
                    cols.update(range(1, len(mline) + 1))

        return comment_positions

    def check(self, document: Document, config: MD033Config) -> list[Violation]:
        """Check for inline HTML violations."""
        violations: list[Violation] = []

        # Normalize allowed elements to lowercase for case-insensitive matching
        allowed = {elem.lower() for elem in config.allowed_elements}
        table_allowed = (
            {elem.lower() for elem in config.table_allowed_elements}
            if config.table_allowed_elements is not None
            else allowed
        )

        # Get lines that are inside code blocks (fenced or indented)
        code_block_lines = document.code_block_lines

        # Get inline code span positions per line
        code_span_positions = document.code_span_positions

        # Get HTML comment positions (handles multi-line comments)
        comment_positions = self._get_html_comment_positions(document)

        # Get lines inside tables
        table_lines: set[int] = set()
        for token in document.tokens:
            if token.type == "table_open" and token.map:
                for line_num in range(token.map[0] + 1, token.map[1] + 1):
                    table_lines.add(line_num)

        for line_num, line in enumerate(document.lines, start=1):
            # Skip lines in code blocks
            if line_num in code_block_lines:
                continue

            # Find all HTML tags on the original line
            for match in self.HTML_TAG_PATTERN.finditer(line):
                element_name = match.group(1).lower()

                # Skip if element is in the appropriate allowed list
                effective_allowed = table_allowed if line_num in table_lines else allowed
                if element_name in effective_allowed:
                    continue

                # Calculate column position (1-indexed)
                column = match.start() + 1

                # Check if this match is inside an inline code span
                if column in code_span_positions.get(line_num, set()):
                    continue

                # Check if this match is inside an HTML comment
                if column in comment_positions.get(line_num, set()):
                    continue

                violations.append(
                    Violation(
                        line=line_num,
                        column=column,
                        rule_id=self.id,
                        rule_name=self.name,
                        message=f"Element <{element_name}> is not allowed",
                        context=document.get_line(line_num),
                    )
                )

        return violations
