from dataclasses import dataclass, field
from typing import Literal

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD055Config(RuleConfig):
    """Configuration for MD055 rule."""

    PipeStyle = Literal[
        "consistent",
        "leading_and_trailing",
        "leading_only",
        "trailing_only",
        "no_leading_or_trailing",
    ]

    style: PipeStyle = field(
        default="consistent",
        metadata={
            "description": "Required table pipe style.",
            "option_descriptions": {
                "consistent": "All rows must match the first row's style",
                "leading_and_trailing": "All rows must have leading and trailing pipes",
                "leading_only": "All rows must have leading pipes only",
                "trailing_only": "All rows must have trailing pipes only",
                "no_leading_or_trailing": "No rows should have leading or trailing pipes",
            },
        },
    )


class MD055(Rule[MD055Config]):
    """Table pipe style should be consistent."""

    id = "MD055"
    name = "table-pipe-style"
    summary = "Table pipe style should be consistent"
    config_class = MD055Config

    description = (
        "This rule ensures that table rows use a consistent style for leading "
        "and trailing pipe characters. By default, the style is determined by "
        "the first table row in the document, and all subsequent rows must match. "
        "Note that text immediately following a table (i.e., not separated by an "
        "empty line) is treated as part of the table per the GFM specification "
        "and may also trigger this rule."
    )

    rationale = (
        "Some parsers have difficulty with tables that are missing their leading "
        "or trailing pipe characters. The use of leading/trailing pipes can also "
        "help provide visual clarity and maintain consistent formatting."
    )

    example_valid = """\
# Consistent Table Pipe Style

| Header 1 | Header 2 |
| -------- | -------- |
| Cell 1   | Cell 2   |
| Cell 3   | Cell 4   |

Another table with the same style:

| Name  | Value |
| ----- | ----- |
| Alpha | 100   |
| Beta  | 200   |
"""

    example_invalid = """\
# Inconsistent Table Pipe Style

| Header 1 | Header 2 |
| -------- | --------
  Cell 1   | Cell 2   |
"""

    def check(self, document: Document, config: MD055Config) -> list[Violation]:
        """Check for table pipe style consistency."""
        violations: list[Violation] = []

        style = config.style

        # Track expected style (for consistent mode)
        expected_leading: bool | None = None
        expected_trailing: bool | None = None

        if style == "leading_and_trailing":
            expected_leading = True
            expected_trailing = True
        elif style == "leading_only":
            expected_leading = True
            expected_trailing = False
        elif style == "trailing_only":
            expected_leading = False
            expected_trailing = True
        elif style == "no_leading_or_trailing":
            expected_leading = False
            expected_trailing = False
        # For "consistent", we'll determine from first row

        # Find all table rows
        table_rows = MD055._get_table_rows(document)

        for line_num in table_rows:
            line_content = document.get_line(line_num)
            if line_content is None:
                continue

            has_leading, has_trailing = self._check_pipe_style(line_content)

            # Set expected style from first row (consistent mode)
            if expected_leading is None:
                expected_leading = has_leading
                expected_trailing = has_trailing
                continue

            # Check for violations
            if has_leading != expected_leading:
                if expected_leading:
                    message = "Missing leading pipe"
                else:
                    message = "Unexpected leading pipe"
                violations.append(
                    Violation(
                        line=line_num,
                        column=1,
                        rule_id=self.id,
                        rule_name=self.name,
                        message=message,
                        context=line_content,
                    )
                )

            if has_trailing != expected_trailing:
                if expected_trailing:
                    message = "Missing trailing pipe"
                else:
                    message = "Unexpected trailing pipe"
                violations.append(
                    Violation(
                        line=line_num,
                        column=len(line_content),
                        rule_id=self.id,
                        rule_name=self.name,
                        message=message,
                        context=line_content,
                    )
                )

        return violations

    @staticmethod
    def _get_table_rows(document: Document) -> list[int]:
        """Get line numbers of all table rows (including delimiter rows).

        Returns:
            List of 1-indexed line numbers for all table rows.
        """
        table_rows: list[int] = []

        for token in document.tokens:
            if token.type == "table_open" and token.map:
                # table.map gives us [start_line, end_line] (0-indexed)
                start_line = token.map[0] + 1  # Convert to 1-indexed
                end_line = token.map[1]  # End line is exclusive

                for line_num in range(start_line, end_line + 1):
                    line_content = document.get_line(line_num)
                    if line_content is not None and "|" in line_content:
                        table_rows.append(line_num)

        return table_rows

    @staticmethod
    def _check_pipe_style(line: str) -> tuple[bool, bool]:
        """Check if a line has leading and trailing pipes.

        Strips blockquote markers (``>``) before checking so that tables
        inside blockquotes are handled correctly.

        Args:
            line: The line content to check.

        Returns:
            Tuple of (has_leading_pipe, has_trailing_pipe).
        """
        stripped = line.strip()
        # Strip blockquote prefixes (e.g., "> ", ">> ")
        while stripped.startswith(">"):
            stripped = stripped[1:].lstrip()
        has_leading = stripped.startswith("|")
        has_trailing = stripped.endswith("|")
        return has_leading, has_trailing
