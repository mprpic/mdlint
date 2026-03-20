import re
from collections.abc import Iterator
from dataclasses import dataclass

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD034Config(RuleConfig):
    """Configuration for MD034 rule."""


class MD034(Rule[MD034Config]):
    """Bare URL used."""

    id = "MD034"
    name = "no-bare-urls"
    summary = "Bare URL used"
    config_class = MD034Config

    description = (
        "This rule is triggered when a URL or email address appears in the "
        "document without being enclosed in angle brackets, link syntax, or "
        "code spans. URLs using `http`, `https`, and `ftp` protocols are checked."
    )

    rationale = (
        "Without angle brackets, a bare URL or email address is not converted "
        "into a clickable link by some Markdown parsers. Wrapping URLs in "
        "angle brackets (`<url>`) or using proper link syntax ensures consistent "
        "rendering across different Markdown processors."
    )

    example_valid = """\
# Document with Proper URLs

Visit <https://www.example.com/> for more information.

Contact us at <user@example.com> for support.

You can also use [example](https://www.example.com/) link syntax.

Not a clickable link: `https://www.example.com`

Reference: [https://example.com]

[example.com]: https://example.com
"""

    example_invalid = """\
# Document with Bare URLs

Visit https://www.example.com/ for more information.

Contact us at user@example.com for support.
"""

    # Pattern to match URLs (http, https, ftp) with balanced parentheses support
    URL_PATTERN = re.compile(
        r"(?<![<\[(])"
        r"(?:https?|ftp)://"
        r"[^\s<>\[\]()\"'`]+"
        r"(?:\([^\s<>\[\]()\"'`]*\)[^\s<>\[\]()\"'`]*)*",
        re.IGNORECASE,
    )

    # Pattern to match email addresses
    EMAIL_PATTERN = re.compile(
        r"(?<![<\[(])(?<![a-zA-Z0-9._%+-])([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(?![>\])])",
        re.IGNORECASE,
    )

    # Pattern to match HTML tags (used to exclude URLs in attributes)
    HTML_TAG_PATTERN = re.compile(r"<[a-zA-Z/][^>]*>")

    TRAILING_PUNCT = ".,:;?!"

    def _find_bare_urls(self, document: Document) -> Iterator[tuple[int, int, int, str]]:
        """Yield bare URL/email matches.

        Yields tuples of (line_num, start, end, bare_text) where start/end are
        0-indexed column positions within the line.
        """
        code_block_lines = document.code_block_lines
        code_span_positions = document.code_span_positions

        for line_num, line in enumerate(document.lines, start=1):
            if line_num in code_block_lines:
                continue

            has_url = "://" in line
            has_email = "@" in line
            if not has_url and not has_email:
                continue

            if Document.REFERENCE_DEF_PATTERN.match(line):
                continue

            html_ranges = (
                [(m.start(), m.end()) for m in self.HTML_TAG_PATTERN.finditer(line)]
                if "<" in line
                else []
            )

            if has_url:
                for match in self.URL_PATTERN.finditer(line):
                    column = match.start() + 1
                    if column in code_span_positions.get(line_num, set()):
                        continue
                    if self._overlaps_ranges(match.start(), match.end(), html_ranges):
                        continue
                    url = match.group(0).rstrip(self.TRAILING_PUNCT)
                    yield line_num, match.start(), match.start() + len(url), url

            if has_email:
                for match in self.EMAIL_PATTERN.finditer(line):
                    column = match.start() + 1
                    if column in code_span_positions.get(line_num, set()):
                        continue
                    if self._overlaps_ranges(match.start(), match.end(), html_ranges):
                        continue
                    email = match.group(1)
                    yield line_num, match.start(1), match.start(1) + len(email), email

    def check(self, document: Document, config: MD034Config) -> list[Violation]:
        """Check for bare URLs in the document."""
        return [
            Violation(
                line=line_num,
                column=start + 1,
                rule_id=self.id,
                rule_name=self.name,
                message=f"Bare URL used: {bare_text}",
                context=document.get_line(line_num),
            )
            for line_num, start, _, bare_text in self._find_bare_urls(document)
        ]

    def fix(self, document: Document, config: MD034Config) -> str | None:
        """Fix bare URLs and emails by wrapping them in angle brackets."""
        matches_by_line: dict[int, list[tuple[int, int, str]]] = {}
        for line_num, start, end, bare_text in self._find_bare_urls(document):
            matches_by_line.setdefault(line_num, []).append((start, end, bare_text))

        if not matches_by_line:
            return None

        lines = document.content.split("\n")
        for line_num, replacements in matches_by_line.items():
            line = lines[line_num - 1]
            for start, end, bare_text in sorted(replacements, key=lambda r: r[0], reverse=True):
                line = line[:start] + f"<{bare_text}>" + line[end:]
            lines[line_num - 1] = line

        return "\n".join(lines)
