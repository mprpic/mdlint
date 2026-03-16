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

    def _find_missing_space_lines(self, document: Document) -> list[tuple[int, str, re.Match[str]]]:
        """Return list of (line_num, raw_line, match) for lines missing spaces."""
        ignored_lines = document.code_block_lines | document.html_block_lines

        results: list[tuple[int, str, re.Match[str]]] = []
        for line_num, line in enumerate(document.lines, start=1):
            if line_num in ignored_lines:
                continue

            stripped = self.BLOCKQUOTE_PREFIX.sub("", line)
            match = self.CLOSED_ATX_PATTERN.match(stripped)
            if not match:
                continue

            if not match.group(2) or not match.group(4):
                results.append((line_num, line, match))

        return results

    def check(self, document: Document, config: MD020Config) -> list[Violation]:
        """Check for missing spaces in closed ATX style headings."""
        violations: list[Violation] = []

        for line_num, line, match in self._find_missing_space_lines(document):
            missing_left = not match.group(2)
            missing_right = not match.group(4)

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

    def fix(self, document: Document, config: MD020Config) -> str | None:
        """Fix missing spaces in closed ATX style headings by inserting spaces."""
        matching_lines = self._find_missing_space_lines(document)
        if not matching_lines:
            return None

        lines = document.content.split("\n")
        for line_num, line, match in matching_lines:
            # Find where the stripped content starts (after blockquote prefix)
            bq_match = self.BLOCKQUOTE_PREFIX.match(line)
            prefix = bq_match.group(0) if bq_match else ""

            opening_hashes = match.group(1)
            left_space = match.group(2)
            content = match.group(3)
            right_space = match.group(4)
            closing_hashes = match.group(5)
            trailing = line[len(prefix) + match.end() :]

            lines[line_num - 1] = (
                prefix
                + opening_hashes
                + (left_space or " ")
                + content
                + (right_space or " ")
                + closing_hashes
                + trailing
            )

        return "\n".join(lines)
