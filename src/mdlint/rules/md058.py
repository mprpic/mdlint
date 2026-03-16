from dataclasses import dataclass

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD058Config(RuleConfig):
    """Configuration for MD058 rule."""


class MD058(Rule[MD058Config]):
    """Tables should be surrounded by blank lines."""

    id = "MD058"
    name = "blanks-around-tables"
    summary = "Tables should be surrounded by blank lines"
    config_class = MD058Config

    description = (
        "This rule enforces blank lines around tables. It triggers when "
        "tables are not preceded or followed by a blank line. The first "
        "table in a document does not require a blank line above, and the "
        "last table at the end of a document does not require a blank line "
        "below."
    )

    rationale = (
        "In addition to aesthetic reasons, some parsers will incorrectly "
        "parse tables that don't have blank lines before and after them. "
        "Consistent spacing around tables improves readability and ensures "
        "proper parsing across different Markdown implementations."
    )

    example_valid = """\
Some text here.

| Header | Header |
| ------ | ------ |
| Cell   | Cell   |

More text here.
"""

    example_invalid = """\
Some text here.
| Header | Header |
| ------ | ------ |
| Cell   | Cell   |
> Blockquote
"""

    def _get_table_ranges(self, document: Document) -> list[tuple[int, int]]:
        """Return 0-indexed (start, end) ranges for table tokens."""
        return [
            (token.map[0], token.map[1])
            for token in document.tokens
            if token.type == "table_open" and token.map
        ]

    def check(self, document: Document, config: MD058Config) -> list[Violation]:
        """Check for blanks-around-tables violations."""
        violations: list[Violation] = []

        for table_start, table_end in self._get_table_ranges(document):
            table_start_line = table_start + 1  # 1-indexed
            table_end_line = table_end  # exclusive, so last line of table

            # Check blank line above
            if table_start_line > 1:
                line_above = document.get_line(table_start_line - 1)
                if line_above is not None and line_above.strip() != "":
                    violations.append(
                        Violation(
                            line=table_start_line,
                            column=1,
                            rule_id=self.id,
                            rule_name=self.name,
                            message="Table should be preceded by a blank line",
                            context=document.get_line(table_start_line),
                        )
                    )

            # Check blank line below
            if table_end_line < len(document.lines):
                line_below = document.get_line(table_end_line + 1)
                if line_below is not None and line_below.strip() != "":
                    violations.append(
                        Violation(
                            line=table_end_line,
                            column=1,
                            rule_id=self.id,
                            rule_name=self.name,
                            message="Table should be followed by a blank line",
                            context=document.get_line(table_end_line),
                        )
                    )

        return violations

    def fix(self, document: Document, config: MD058Config) -> str | None:
        """Fix blanks-around-tables violations by inserting missing blank lines."""
        table_ranges = self._get_table_ranges(document)

        if not table_ranges:
            return None

        lines = document.content.split("\n")
        num_doc_lines = len(document.lines)
        changed = False

        # Process tables from bottom to top so insertions don't shift indices
        for table_start, table_end in reversed(table_ranges):
            # table_start is 0-indexed line of first table row
            # table_end is 0-indexed exclusive end (first line after table)

            # Fix blank line below
            if table_end < num_doc_lines:
                if lines[table_end].strip() != "":
                    lines.insert(table_end, "")
                    changed = True

            # Fix blank line above
            if table_start > 0:
                if lines[table_start - 1].strip() != "":
                    lines.insert(table_start, "")
                    changed = True

        if not changed:
            return None

        return "\n".join(lines)
