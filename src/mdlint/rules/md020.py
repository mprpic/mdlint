import re
from dataclasses import dataclass

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD020Config(RuleConfig):
    """Configuration for MD020 rule."""


class MD020(Rule[MD020Config]):
    """No space inside hashes on closed ATX style heading."""

    id = "MD020"
    name = "no-missing-space-closed-atx"
    summary = "No space inside hashes on closed ATX style heading"
    config_class = MD020Config

    description = (
        "This rule is triggered when spaces are missing inside the hash "
        "characters in a closed ATX style heading. Both sides of the heading "
        "text must have a space separating it from the hash characters."
    )

    rationale = (
        "Violations of this rule can lead to improperly rendered content. "
        "Some Markdown parsers require spaces around heading text in closed "
        "ATX style headings for proper rendering."
    )

    example_valid = """\
# Heading 1 #

## Heading 2 ##

### Heading 3 ###

Proper spacing around heading text in closed ATX style.
"""

    example_invalid = """\
#Heading 1#

##Heading 2##

###Heading 3###

Missing spaces inside hashes on closed ATX style headings.
"""

    # Pattern to match closed ATX headings with potential missing spaces
    # Matches lines starting with 1-6 hashes, content, and ending with hashes
    CLOSED_ATX_PATTERN = re.compile(
        r"^(#{1,6})([ \t]?)([^#\s]|[^#\s].*?[^#\s\\]|[^#\s\\])([ \t]?)(#{1,6})\s*$"
    )

    # Pattern to strip blockquote prefixes from lines
    BLOCKQUOTE_PREFIX = re.compile(r"^(\s*>\s*)+")

    def check(self, document: Document, config: MD020Config) -> list[Violation]:
        """Check for missing spaces in closed ATX style headings."""
        violations: list[Violation] = []

        # Build set of ignored lines (code blocks + HTML blocks), matching MD018 pattern
        ignored_lines = self._get_code_block_lines(document)
        for token in document.tokens:
            if token.type == "html_block" and token.map:
                for ln in range(token.map[0] + 1, token.map[1] + 1):
                    ignored_lines.add(ln)

        for line_num, line in enumerate(document.lines, start=1):
            if line_num in ignored_lines:
                continue

            # Strip blockquote prefix before matching
            stripped = self.BLOCKQUOTE_PREFIX.sub("", line)

            match = self.CLOSED_ATX_PATTERN.match(stripped)
            if not match:
                continue

            left_space = match.group(2)
            right_space = match.group(4)

            missing_left = not left_space
            missing_right = not right_space

            if missing_left or missing_right:
                if missing_left and missing_right:
                    message = "No space inside hashes on closed ATX heading"
                elif missing_left:
                    message = "No space after opening hashes on closed ATX heading"
                else:
                    message = "No space before closing hashes on closed ATX heading"

                violations.append(
                    Violation(
                        line=line_num,
                        column=1,
                        rule_id=self.id,
                        rule_name=self.name,
                        message=message,
                        context=line,
                    )
                )

        return violations
