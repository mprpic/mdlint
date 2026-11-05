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

    @staticmethod
    def _scan_line(line: str) -> Iterator[tuple[int, int, str, str]]:
        """Yield (start, end, link_text, link_dest) for each reversed link in a line.

        A match is `(text)[dest]` where the `(` is not escaped, the text holds no
        parentheses, the destination does not start with `^` (a footnote) and the `]` is
        not followed by `(`. Matches do not overlap. This is a single left-to-right scan
        because the equivalent regex backtracked quadratically on long lines of
        unclosed candidates such as `(a)[(a)[(a)[...`.
        """
        search_from = 0  # end of the previous match
        previous = -1  # index of the previous ")[" candidate
        close = -1  # next "]" at or after the current destination, found once and reused
        pos = line.find(")[")
        while pos >= 0:
            # The text cannot contain ")", so its "(" lies after the previous candidate;
            # bounding the search there keeps the whole scan linear.
            lower = max(search_from, previous + 1)
            previous = pos
            opener = max(line.rfind("(", lower, pos), line.rfind(")", lower, pos))
            dest_start = pos + 2
            if (
                opener >= 0
                and line[opener] == "("
                and opener < pos - 1
                and (opener == 0 or line[opener - 1] != "\\")
                and dest_start < len(line)
                and line[dest_start] not in "]^"
            ):
                if close < dest_start:
                    close = line.find("]", dest_start)
                    if close < 0:
                        return
                if line[close + 1 : close + 2] != "(":
                    yield opener, close + 1, line[opener + 1 : pos], line[dest_start:close]
                    search_from = close + 1
            pos = line.find(")[", max(pos + 1, search_from))

    def _find_reversed_links(self, document: Document) -> Iterator[tuple[int, int, int, str, str]]:
        """Yield reversed link matches with metadata.

        Yields tuples of (line_num, start, end, link_text, link_dest), where start and
        end are the 0-indexed span of the reversed link in the line.
        """
        code_block_lines = document.code_block_lines
        html_block_lines = document.html_block_lines
        inline_code_columns = document.code_span_positions

        for line_num, line in enumerate(document.lines, start=1):
            if line_num in code_block_lines or line_num in html_block_lines:
                continue

            if ")[" not in line:
                continue

            for start, end, link_text, link_dest in self._scan_line(line):
                if link_text.endswith("\\") or link_dest.endswith("\\"):
                    continue

                code_cols = inline_code_columns.get(line_num, set())
                if code_cols and start + 1 in code_cols:
                    continue

                yield line_num, start, end, link_text, link_dest

    def check(self, document: Document, config: MD011Config) -> list[Violation]:
        """Check for reversed link syntax."""
        violations: list[Violation] = []

        for line_num, start, end, _, _ in self._find_reversed_links(document):
            reversed_link = document.lines[line_num - 1][start:end]
            violations.append(
                Violation(
                    line=line_num,
                    column=start + 1,
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
        matches_by_line: dict[int, list[tuple[int, int, str, str]]] = {}
        for line_num, start, end, link_text, link_dest in self._find_reversed_links(document):
            matches_by_line.setdefault(line_num, []).append((start, end, link_text, link_dest))

        if not matches_by_line:
            return None

        lines = document.content.split("\n")
        for line_num, line_matches in matches_by_line.items():
            line = lines[line_num - 1]
            # Process in reverse order to preserve column positions
            for start, end, link_text, link_dest in reversed(line_matches):
                line = line[:start] + f"[{link_text}]({link_dest})" + line[end:]
            lines[line_num - 1] = line

        return "\n".join(lines)
