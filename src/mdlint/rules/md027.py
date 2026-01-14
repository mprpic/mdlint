import re
from dataclasses import dataclass

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD027Config(RuleConfig):
    """Configuration for MD027 rule."""


class MD027(Rule[MD027Config]):
    """Multiple spaces after blockquote symbol."""

    id = "MD027"
    name = "no-multiple-space-blockquote"
    summary = "Multiple spaces after blockquote symbol"
    config_class = MD027Config

    description = (
        "This rule is triggered when blockquote lines contain more than one "
        "space after the blockquote marker (`>`). The standard format requires "
        "exactly one space between the `>` and the content."
    )

    rationale = (
        "Extra space has no purpose and does not affect the rendering of "
        "content. Using a single space keeps the source clean and consistent."
    )

    example_valid = """\
> This is a blockquote with correct
> indentation.
"""

    example_invalid = """\
>  This is a blockquote with bad indentation
>  there should only be one.
"""

    # Pattern to match blockquote marker followed by 2+ spaces
    # Matches: optional whitespace, one or more >, then 2+ spaces
    MULTIPLE_SPACES_PATTERN = re.compile(r"^(\s*>+)\s{2,}")

    def check(self, document: Document, config: MD027Config) -> list[Violation]:
        """Check for multiple spaces after blockquote marker."""
        violations: list[Violation] = []
        code_block_lines = self._get_code_block_lines(document)

        for line_num, line in enumerate(document.lines, start=1):
            if line_num in code_block_lines:
                continue
            match = self.MULTIPLE_SPACES_PATTERN.match(line)
            if match:
                # Calculate column position (after the > marker)
                column = len(match.group(1)) + 1
                violations.append(
                    Violation(
                        line=line_num,
                        column=column,
                        rule_id=self.id,
                        rule_name=self.name,
                        message="Multiple spaces after blockquote symbol",
                        context=line,
                    )
                )

        return violations
