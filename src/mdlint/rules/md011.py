import re
from dataclasses import dataclass

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD011Config(RuleConfig):
    """Configuration for MD011 rule."""


class MD011(Rule[MD011Config]):
    """Reversed link syntax."""

    id = "MD011"
    name = "no-reversed-links"
    summary = "Reversed link syntax"
    config_class = MD011Config

    description = (
        "This rule is triggered when text that appears to be a link is "
        "encountered, but where the syntax appears to have been reversed "
        "(the `[]` and `()` are reversed).\n\n"
        "Note: Footnotes such as `(text)[^1]` do not trigger this rule."
    )

    rationale = (
        "Reversed links are not rendered as usable links. The text will "
        "appear literally as `(text)[url]` instead of being converted to a "
        "clickable hyperlink. This is a common mistake where the author "
        "specified the incorrect order of link components."
    )

    example_valid = """\
# Valid Links

This is a document with [correct link syntax](https://www.example.com/).

Here is [another link](https://example.org/page) in a sentence.

Reference links [like this][ref] are also fine.

[ref]: https://example.com/reference
"""

    example_invalid = """\
# Reversed Links

This is a document with (incorrect link syntax)[https://www.example.com/].

Here is (another bad link)[https://example.org/page] in a sentence.
"""

    # Pattern to match reversed links: (text)[url]
    # - Must not start with backslash (escaped)
    # - Captures: (1) preceding char, (2) link text, (3) link destination
    # - Does not match footnote references [^...] or if followed by (
    REVERSED_LINK_PATTERN = re.compile(r"(^|[^\\])\(([^()]+)\)\[([^]^][^]]*)](?!\()")

    def check(self, document: Document, config: MD011Config) -> list[Violation]:
        """Check for reversed link syntax."""
        violations: list[Violation] = []

        # Build set of line numbers inside code blocks (fenced and indented)
        code_block_lines = self._get_code_block_lines(document)

        # Build map of inline code column ranges per line
        inline_code_columns = self._get_code_span_positions(document)

        for line_num, line in enumerate(document.lines, start=1):
            # Skip lines in code blocks
            if line_num in code_block_lines:
                continue

            # Find all reversed links on this line
            for match in self.REVERSED_LINK_PATTERN.finditer(line):
                pre_char = match.group(1)
                link_text = match.group(2)
                link_dest = match.group(3)

                # Skip if link text or destination ends with backslash
                if link_text.endswith("\\") or link_dest.endswith("\\"):
                    continue

                # Calculate column position (1-indexed)
                column = match.start() + len(pre_char) + 1

                # Check if this match is inside an inline code span
                code_cols = inline_code_columns.get(line_num, set())
                if code_cols and column in code_cols:
                    continue

                reversed_link = match.group(0)[len(pre_char) :]
                violations.append(
                    Violation(
                        line=line_num,
                        column=column,
                        rule_id=self.id,
                        rule_name=self.name,
                        message=f"Reversed link syntax: {reversed_link}",
                        context=document.get_line(line_num),
                    )
                )

        return violations
