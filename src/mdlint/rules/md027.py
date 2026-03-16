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

    def _find_multiple_space_lines(self, document: Document) -> list[tuple[int, re.Match[str]]]:
        """Return list of (line_num, match) for blockquote lines with multiple spaces."""
        code_block_lines = document.code_block_lines
        results: list[tuple[int, re.Match[str]]] = []

        for line_num, line in enumerate(document.lines, start=1):
            if line_num in code_block_lines:
                continue
            match = self.MULTIPLE_SPACES_PATTERN.match(line)
            if match:
                results.append((line_num, match))

        return results

    def check(self, document: Document, config: MD027Config) -> list[Violation]:
        """Check for multiple spaces after blockquote marker."""
        violations: list[Violation] = []

        for line_num, match in self._find_multiple_space_lines(document):
            # Calculate column position (after the > marker)
            column = len(match.group(1)) + 1
            violations.append(
                Violation(
                    line=line_num,
                    column=column,
                    rule_id=self.id,
                    rule_name=self.name,
                    message="Multiple spaces after blockquote symbol",
                    context=document.get_line(line_num),
                )
            )

        return violations

    def fix(self, document: Document, config: MD027Config) -> str | None:
        """Fix multiple spaces after blockquote marker by collapsing to one."""
        matching_lines = self._find_multiple_space_lines(document)
        if not matching_lines:
            return None

        lines = document.content.split("\n")
        for line_num, match in matching_lines:
            prefix = match.group(1)
            rest = lines[line_num - 1][match.end() :]
            lines[line_num - 1] = prefix + " " + rest

        return "\n".join(lines)
