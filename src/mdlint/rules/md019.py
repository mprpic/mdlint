import re
from dataclasses import dataclass

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD019Config(RuleConfig):
    """Configuration for MD019 rule."""


class MD019(Rule[MD019Config]):
    """Multiple spaces after hash on ATX style heading."""

    id = "MD019"
    name = "no-multiple-space-atx"
    summary = "Multiple spaces after hash on ATX style heading"
    config_class = MD019Config

    description = (
        "This rule is triggered when more than one space is used to separate "
        "the heading text from the hash characters in an ATX style heading."
    )

    rationale = (
        "Extra space has no purpose and does not affect the rendering of "
        "content. Using a single space keeps the source clean and consistent."
    )

    example_valid = """\
# Heading 1

## Heading 2

### Heading 3

Headings with single space after hash.
"""

    example_invalid = """\
#  Heading 1

##  Heading 2

###  Heading 3

Headings with multiple spaces after hash.
"""

    # Pattern to match ATX heading with multiple spaces after hash
    MULTIPLE_SPACES_PATTERN = re.compile(r"^(#{1,6})\s{2,}")

    def check(self, document: Document, config: MD019Config) -> list[Violation]:
        """Check for multiple spaces after hash in ATX headings."""
        violations: list[Violation] = []

        for token in document.tokens:
            if token.type != "heading_open":
                continue

            # Only check ATX-style headings (markup starts with #)
            if not token.markup.startswith("#"):
                continue

            line = token.map[0] + 1 if token.map else 1
            raw_line = document.get_line(line)

            if raw_line and self.MULTIPLE_SPACES_PATTERN.match(raw_line):
                violations.append(
                    Violation(
                        line=line,
                        column=1,
                        rule_id=self.id,
                        rule_name=self.name,
                        message="Multiple spaces after hash on ATX style heading",
                        context=raw_line,
                    )
                )

        return violations
