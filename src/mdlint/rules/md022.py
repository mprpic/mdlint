from dataclasses import dataclass, field

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD022Config(RuleConfig):
    """Configuration for MD022 rule."""

    lines_above: int = field(
        default=1,
        metadata={
            "description": "Number of blank lines required before headings. Use -1 to disable.",
        },
    )
    lines_below: int = field(
        default=1,
        metadata={
            "description": "Number of blank lines required after headings. Use -1 to disable.",
        },
    )


class MD022(Rule[MD022Config]):
    """Headings should be surrounded by blank lines."""

    id = "MD022"
    name = "blanks-around-headings"
    summary = "Headings should be surrounded by blank lines"
    config_class = MD022Config

    description = (
        "This rule enforces blank lines around headings. It triggers when "
        "headings are not preceded or followed by at least the required "
        "number of blank lines (default: 1 each). Extra blank lines beyond "
        "the requirement are not flagged. The first heading in a document "
        "does not require blank lines above, and the last heading at the "
        "end of a document does not require blank lines below. Set "
        "`lines_above` or `lines_below` to `-1` to disable the "
        "respective check."
    )

    rationale = (
        "Aside from aesthetic reasons, some Markdown parsers "
        "will not parse headings that don't have a blank line before them, "
        "and will parse them as regular text. Consistent spacing around "
        "headings improves readability and ensures proper parsing."
    )

    example_valid = """\
# Heading 1

Some text here.

## Heading 2

Some more text here.
"""

    example_invalid = """\
# Heading 1
Some text here.

Some more text.
## Heading 2
"""

    def check(self, document: Document, config: MD022Config) -> list[Violation]:
        """Check for blanks-around-headings violations."""
        violations: list[Violation] = []

        lines_above = config.lines_above
        lines_below = config.lines_below

        for token in document.tokens:
            if token.type == "heading_open" and token.map:
                heading_start_line = token.map[0] + 1  # 1-indexed
                heading_end_line = token.map[1]  # exclusive, so last line is map[1]

                # Check blank lines above
                if lines_above > 0 and heading_start_line > 1:
                    blank_count = self._count_blank_lines_above(document, heading_start_line)
                    if blank_count < lines_above:
                        violations.append(
                            Violation(
                                line=heading_start_line,
                                column=1,
                                rule_id=self.id,
                                rule_name=self.name,
                                message=(
                                    f"Expected {lines_above} blank line(s) above "
                                    f"heading, found {blank_count}"
                                ),
                                context=document.get_line(heading_start_line),
                            )
                        )

                # Check blank lines below
                if lines_below > 0 and heading_end_line < len(document.lines):
                    blank_count = self._count_blank_lines_below(document, heading_end_line)
                    if blank_count < lines_below:
                        violations.append(
                            Violation(
                                line=heading_start_line,
                                column=1,
                                rule_id=self.id,
                                rule_name=self.name,
                                message=(
                                    f"Expected {lines_below} blank line(s) below "
                                    f"heading, found {blank_count}"
                                ),
                                context=document.get_line(heading_start_line),
                            )
                        )

        return violations

    def fix(self, document: Document, config: MD022Config) -> str | None:
        """Fix blanks-around-headings violations by inserting missing blank lines."""
        lines_above = config.lines_above
        lines_below = config.lines_below

        if lines_above <= 0 and lines_below <= 0:
            return None

        # Collect heading info: list of (start_line_0indexed, end_line_0indexed_exclusive)
        headings: list[tuple[int, int]] = []
        for token in document.tokens:
            if token.type == "heading_open" and token.map:
                headings.append((token.map[0], token.map[1]))

        if not headings:
            return None

        lines = document.content.split("\n")
        num_doc_lines = len(document.lines)
        changed = False

        # Process headings from bottom to top so insertions don't shift indices
        for heading_start, heading_end in reversed(headings):
            # heading_start is 0-indexed line of the heading
            # heading_end is 0-indexed exclusive end (first line after heading)

            # Fix blank lines below
            if lines_below > 0 and heading_end < num_doc_lines:
                existing_below = 0
                idx = heading_end
                while idx < num_doc_lines and lines[idx].strip() == "":
                    existing_below += 1
                    idx += 1
                if existing_below < lines_below:
                    blanks_to_add = lines_below - existing_below
                    for _ in range(blanks_to_add):
                        lines.insert(heading_end, "")
                    changed = True

            # Fix blank lines above
            if lines_above > 0 and heading_start > 0:
                existing_above = 0
                idx = heading_start - 1
                while idx >= 0 and lines[idx].strip() == "":
                    existing_above += 1
                    idx -= 1
                if existing_above < lines_above:
                    blanks_to_add = lines_above - existing_above
                    for _ in range(blanks_to_add):
                        lines.insert(heading_start, "")
                    changed = True

        if not changed:
            return None

        return "\n".join(lines)

    @staticmethod
    def _count_blank_lines_above(document: Document, heading_line: int) -> int:
        """Count consecutive blank lines immediately above a heading.

        Args:
            document: The document being checked.
            heading_line: 1-indexed line number of the heading.

        Returns:
            Number of consecutive blank lines above the heading.
        """
        count = 0
        line_num = heading_line - 1

        while line_num >= 1:
            line_content = document.get_line(line_num)
            if line_content is not None and line_content.strip() == "":
                count += 1
                line_num -= 1
            else:
                break

        return count

    @staticmethod
    def _count_blank_lines_below(document: Document, heading_end_line: int) -> int:
        """Count consecutive blank lines immediately below a heading.

        Args:
            document: The document being checked.
            heading_end_line: The line after the heading ends (from token.map[1]).

        Returns:
            Number of consecutive blank lines below the heading.
        """
        count = 0
        line_num = heading_end_line + 1  # First line after heading

        while line_num <= len(document.lines):
            line_content = document.get_line(line_num)
            if line_content is not None and line_content.strip() == "":
                count += 1
                line_num += 1
            else:
                break

        return count
