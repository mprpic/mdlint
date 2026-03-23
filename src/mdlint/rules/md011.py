import re
from collections.abc import Iterator
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

    def _find_reversed_links(
        self, document: Document
    ) -> Iterator[tuple[int, re.Match[str], str, str, str, int]]:
        """Yield reversed link matches with metadata.

        Yields tuples of (line_num, match, pre_char, link_text, link_dest, column).
        """
        code_block_lines = document.code_block_lines
        html_block_lines = document.html_block_lines
        inline_code_columns = document.code_span_positions

        for line_num, line in enumerate(document.lines, start=1):
            if line_num in code_block_lines or line_num in html_block_lines:
                continue

            if ")[" not in line:
                continue

            for match in self.REVERSED_LINK_PATTERN.finditer(line):
                pre_char = match.group(1)
                link_text = match.group(2)
                link_dest = match.group(3)

                if link_text.endswith("\\") or link_dest.endswith("\\"):
                    continue

                column = match.start() + len(pre_char) + 1
                code_cols = inline_code_columns.get(line_num, set())
                if code_cols and column in code_cols:
                    continue

                yield line_num, match, pre_char, link_text, link_dest, column

    def check(self, document: Document, config: MD011Config) -> list[Violation]:
        """Check for reversed link syntax."""
        violations: list[Violation] = []

        for line_num, match, pre_char, _, _, column in self._find_reversed_links(document):
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

    def fix(self, document: Document, config: MD011Config) -> str | None:
        """Fix reversed link syntax by swapping (text)[url] to [text](url)."""
        # Group matches by line number, collecting in reverse order per line
        matches_by_line: dict[int, list[tuple[re.Match[str], str, str, str]]] = {}
        for line_num, match, pre_char, link_text, link_dest, _ in self._find_reversed_links(
            document
        ):
            matches_by_line.setdefault(line_num, []).append((match, pre_char, link_text, link_dest))

        if not matches_by_line:
            return None

        lines = document.content.split("\n")
        for line_num, line_matches in matches_by_line.items():
            line = lines[line_num - 1]
            # Process in reverse order to preserve column positions
            for match, pre_char, link_text, link_dest in reversed(line_matches):
                start = match.start() + len(pre_char)
                line = line[:start] + f"[{link_text}]({link_dest})" + line[match.end() :]
            lines[line_num - 1] = line

        return "\n".join(lines)
