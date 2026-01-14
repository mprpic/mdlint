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

    def check(self, document: Document, config: MD021Config) -> list[Violation]:
        """Check for multiple spaces in closed ATX style headings."""
        violations: list[Violation] = []

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
            stripped = self.BLOCKQUOTE_PREFIX.sub("", raw_line)

            match = self.CLOSED_ATX_PATTERN.match(stripped)
            if not match:
                continue

            left_space = match.group(2)
            right_space = match.group(4)

            # Check for multiple spaces (more than one space/tab)
            multiple_left = len(left_space) > 1
            multiple_right = len(right_space) > 1

            if multiple_left or multiple_right:
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
