import re
from dataclasses import dataclass

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD021Config(RuleConfig):
    """Configuration for MD021 rule."""


class MD021(Rule[MD021Config]):
    """Multiple spaces inside hashes on closed ATX style heading."""

    id = "MD021"
    name = "no-multiple-space-closed-atx"
    summary = "Multiple spaces inside hashes on closed ATX style heading"
    config_class = MD021Config

    description = (
        "This rule is triggered when more than one space is used to separate "
        "the heading text from the hash characters in a closed ATX style heading. "
        "The violation can occur on either side of the heading text."
    )

    rationale = (
        "Extra space has no purpose and does not affect the rendering of "
        "content. Using a single space keeps the source clean and consistent."
    )

    example_valid = """\
# Heading 1 #

## Heading 2 ##

### Heading 3 ###

Closed ATX headings with single space inside hashes.
"""

    example_invalid = """\
#  Heading 1  #

##  Heading 2  ##

###  Heading 3  ###

Closed ATX headings with multiple spaces inside hashes.
"""

    # Pattern to match closed ATX headings with potential multiple spaces
    # Matches lines starting with 1-6 hashes, spaces, content, spaces, and ending with hashes
    CLOSED_ATX_PATTERN = re.compile(r"^(#{1,6})([ \t]+)(.+?)([ \t]+)(#{1,6})\s*$")

    # Pattern to strip blockquote prefixes from lines
    BLOCKQUOTE_PREFIX = re.compile(r"^(\s*>\s*)+")

    def _find_multiple_space_lines(
        self, document: Document
    ) -> list[tuple[int, str, str, re.Match[str]]]:
        """Return (line_num, raw_line, bq_prefix, match) for headings with multiple spaces."""
        results: list[tuple[int, str, str, re.Match[str]]] = []

        for token in document.tokens:
            if token.type != "heading_open":
                continue

            # Only check ATX-style headings (markup starts with #)
            if not token.markup.startswith("#"):
                continue

            line_num = token.map[0] + 1 if token.map else 1
            raw_line = document.get_line(line_num)

            if not raw_line:
                continue

            # Strip blockquote prefix before matching
            bq_match = self.BLOCKQUOTE_PREFIX.match(raw_line)
            prefix = bq_match.group(0) if bq_match else ""
            stripped = raw_line[len(prefix) :]

            match = self.CLOSED_ATX_PATTERN.match(stripped)
            if not match:
                continue

            left_space = match.group(2)
            right_space = match.group(4)

            if len(left_space) > 1 or len(right_space) > 1:
                results.append((line_num, raw_line, prefix, match))

        return results

    def check(self, document: Document, config: MD021Config) -> list[Violation]:
        """Check for multiple spaces in closed ATX style headings."""
        violations: list[Violation] = []

        for line_num, raw_line, _, match in self._find_multiple_space_lines(document):
            left_space = match.group(2)
            right_space = match.group(4)

            multiple_left = len(left_space) > 1
            multiple_right = len(right_space) > 1

            if multiple_left and multiple_right:
                message = "Multiple spaces inside hashes on closed ATX heading"
            elif multiple_left:
                message = "Multiple spaces after opening hashes on closed ATX heading"
            else:
                message = "Multiple spaces before closing hashes on closed ATX heading"

            violations.append(
                Violation(
                    line=line_num,
                    column=1,
                    rule_id=self.id,
                    rule_name=self.name,
                    message=message,
                    context=raw_line,
                )
            )

        return violations

    def fix(self, document: Document, config: MD021Config) -> str | None:
        """Fix multiple spaces inside hashes by collapsing to a single space."""
        matching_lines = self._find_multiple_space_lines(document)
        if not matching_lines:
            return None

        lines = document.content.split("\n")
        for line_num, _, prefix, match in matching_lines:
            opening_hashes = match.group(1)
            content = match.group(3)
            closing_hashes = match.group(5)

            lines[line_num - 1] = f"{prefix}{opening_hashes} {content} {closing_hashes}"

        return "\n".join(lines)
