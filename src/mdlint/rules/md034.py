import re
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
        "code spans. URLs using http, https, and ftp protocols are checked."
    )

    rationale = (
        "Without angle brackets, a bare URL or email address is not converted "
        "into a clickable link by some Markdown parsers. Wrapping URLs in "
        "angle brackets (<url>) or using proper link syntax ensures consistent "
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

    # Pattern to match reference link definitions: [label]: url
    REFERENCE_DEF_PATTERN = re.compile(r"^\s*\[[^\]]+\]:\s*")

    # Pattern to match HTML tags (used to exclude URLs in attributes)
    HTML_TAG_PATTERN = re.compile(r"<[a-zA-Z/][^>]*>")

    TRAILING_PUNCT = ".,:;?!"

    def check(self, document: Document, config: MD034Config) -> list[Violation]:
        """Check for bare URLs in the document."""
        violations: list[Violation] = []

        code_block_lines = self._get_code_block_lines(document)
        code_span_positions = self._get_code_span_positions(document)

        for line_num, line in enumerate(document.lines, start=1):
            if line_num in code_block_lines:
                continue

            if self.REFERENCE_DEF_PATTERN.match(line):
                continue

            # Find HTML tag ranges to exclude URLs inside attributes
            html_ranges = [(m.start(), m.end()) for m in self.HTML_TAG_PATTERN.finditer(line)]

            # Check for bare URLs
            for match in self.URL_PATTERN.finditer(line):
                column = match.start() + 1

                if column in code_span_positions.get(line_num, set()):
                    continue

                if self._overlaps_ranges(match.start(), match.end(), html_ranges):
                    continue

                url = match.group(0).rstrip(self.TRAILING_PUNCT)
                violations.append(
                    Violation(
                        line=line_num,
                        column=column,
                        rule_id=self.id,
                        rule_name=self.name,
                        message=f"Bare URL used: {url}",
                        context=document.get_line(line_num),
                    )
                )

            # Check for bare email addresses
            for match in self.EMAIL_PATTERN.finditer(line):
                column = match.start() + 1

                if column in code_span_positions.get(line_num, set()):
                    continue

                if self._overlaps_ranges(match.start(), match.end(), html_ranges):
                    continue

                email = match.group(1)
                violations.append(
                    Violation(
                        line=line_num,
                        column=column,
                        rule_id=self.id,
                        rule_name=self.name,
                        message=f"Bare URL used: {email}",
                        context=document.get_line(line_num),
                    )
                )

        return violations
