import re
from dataclasses import dataclass

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD023Config(RuleConfig):
    """Configuration for MD023 rule."""


class MD023(Rule[MD023Config]):
    """Headings must start at the beginning of the line."""

    id = "MD023"
    name = "heading-start-left"
    summary = "Headings must start at the beginning of the line"
    config_class = MD023Config
    preserves_rendering = True

    description = (
        "This rule is triggered when a heading is preceded by one or more "
        "spaces. Headings must start at the very beginning of the line without "
        "any leading whitespace. Headings inside list items and blockquotes "
        "are not flagged, as their indentation is structural."
    )

    rationale = (
        "Headings that don't start at the beginning of the line will not be "
        "parsed as headings and will instead appear as regular text. This can "
        "cause the document structure to break and the heading to not render "
        "properly."
    )

    example_valid = """\
# Heading 1

## Heading 2

### Heading 3

Headings starting at the beginning of the line.
"""

    example_invalid = """\
  # Indented Heading 1

  ## Indented Heading 2

  ### Indented Heading 3

  Indented Setext Heading 1
===========================

  Indented Setext Heading 2
---------------------------

Headings with leading spaces.
"""

    # Pattern to match indented ATX-style headings (not in blockquotes). Only 1-3 spaces:
    # a tab or a fourth space reaches column 4, which makes the line indented code or
    # paragraph continuation text rather than a heading.
    INDENTED_ATX_PATTERN = re.compile(r"^ {1,3}#{1,6}(?:\s|$)")

    def _find_indented_heading_lines(self, document: Document) -> set[int]:
        """Return set of 1-indexed line numbers with indented headings."""
        skip_lines = (
            document.code_block_lines
            | document.html_block_lines
            | document.front_matter_lines
            | self._get_list_item_lines(document)
        )
        result: set[int] = set()

        # Find indented setext headings (parsed as heading tokens)
        list_depth = 0
        for token in document.tokens:
            if token.type == "list_item_open":
                list_depth += 1
            elif token.type == "list_item_close":
                list_depth -= 1
            elif token.type == "heading_open" and token.map and list_depth == 0:
                # Setext headings have markup of = or -
                if token.markup in ("=", "-"):
                    line_num = token.map[0] + 1  # 1-indexed
                    raw_line = document.get_line(line_num)
                    if raw_line and raw_line[0] in (" ", "\t"):
                        result.add(line_num)

        # Find indented ATX-style headings (not parsed as headings)
        for line_num, line in enumerate(document.lines, start=1):
            # Skip lines inside code blocks, HTML blocks, front matter or list items
            if line_num in skip_lines:
                continue

            # Check if line looks like an indented ATX heading
            if self.INDENTED_ATX_PATTERN.match(line):
                result.add(line_num)

        return result

    def check(self, document: Document, config: MD023Config) -> list[Violation]:
        """Check for headings not starting at beginning of line."""
        violations: list[Violation] = []

        for line_num in sorted(self._find_indented_heading_lines(document)):
            violations.append(
                Violation(
                    line=line_num,
                    column=1,
                    rule_id=self.id,
                    rule_name=self.name,
                    message="Heading must start at the beginning of the line",
                    context=document.get_line(line_num),
                )
            )

        return violations

    def fix(self, document: Document, config: MD023Config) -> str | None:
        """Fix headings by removing leading whitespace."""
        fix_lines = self._find_indented_heading_lines(document)
        if not fix_lines:
            return None

        lines = document.content.split("\n")
        for line_num in fix_lines:
            lines[line_num - 1] = lines[line_num - 1].lstrip()

        return "\n".join(lines)

    @staticmethod
    def _get_list_item_lines(document: Document) -> set[int]:
        """Get set of line numbers that are inside list items."""
        lines: set[int] = set()
        for token in document.tokens:
            if token.type == "list_item_open" and token.map:
                start_line = token.map[0] + 1
                end_line = token.map[1]
                for line_num in range(start_line, end_line + 1):
                    lines.add(line_num)
        return lines
