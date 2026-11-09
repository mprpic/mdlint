from dataclasses import dataclass

from mdlint.document import Document, is_blank_line
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
    preserves_rendering = True

    description = (
        "This rule enforces blank lines around tables. It triggers when "
        "tables are not preceded or followed by a blank line. The first "
        "table in a document does not require a blank line above, and the "
        "last table at the end of a document does not require a blank line "
        "below.\n\n"
        "Lines holding only blockquote markers (`>`) or HTML comments count as "
        "blank, so tables inside blockquotes and tables directly below a "
        "directive comment are accepted. A table that opens a list item whose "
        "marker sits alone on the line above needs no blank line above it, "
        "because a blank line there would end the list item."
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
            if table_start_line > 1 and not document.follows_bare_list_marker(table_start):
                line_above = document.get_line(table_start_line - 1)
                if line_above is not None and not is_blank_line(line_above):
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
                if line_below is not None and not is_blank_line(line_below):
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
                if not is_blank_line(lines[table_end]):
                    lines.insert(table_end, document.blank_line_between(table_end, table_end + 1))
                    changed = True

            # Fix blank line above
            if table_start > 0 and not document.follows_bare_list_marker(table_start):
                if not is_blank_line(lines[table_start - 1]):
                    blank = document.blank_line_between(table_start, table_start + 1)
                    lines.insert(table_start, blank)
                    changed = True

        if not changed:
            return None

        return "\n".join(lines)
