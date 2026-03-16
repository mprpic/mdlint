from dataclasses import dataclass, field

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD012Config(RuleConfig):
    """Configuration for MD012 rule."""

    maximum: int = field(
        default=1,
        metadata={
            "description": (
                "Maximum number of consecutive blank lines allowed. Default is 1, "
                "meaning only single blank lines are permitted."
            ),
        },
    )


class MD012(Rule[MD012Config]):
    """No multiple consecutive blank lines."""

    id = "MD012"
    name = "no-multiple-blanks"
    summary = "No multiple consecutive blank lines"
    config_class = MD012Config

    description = (
        "This rule detects multiple consecutive blank lines in markdown "
        "documents. It triggers when the number of consecutive blank lines "
        "exceeds the configured maximum (default: 1). Multiple consecutive "
        "blank lines inside code blocks and front matter are excluded and "
        "will not trigger this rule."
    )

    rationale = (
        "Except in a code block, blank lines serve no purpose and do not "
        "affect the rendering of content. Multiple consecutive blank lines "
        "create unnecessary whitespace in source files and can indicate "
        "formatting inconsistencies."
    )

    example_valid = """\
# Heading

Some text here.

Some more text here.
"""

    example_invalid = """\
# Heading

Some text here.


Some more text here.
"""

    def _get_excluded_lines(self, document: Document) -> set[int]:
        """Get line numbers inside code blocks or front matter."""
        excluded = document.code_block_lines
        for token in document.tokens:
            if token.type == "front_matter" and token.map:
                for ln in range(token.map[0] + 1, token.map[1] + 1):
                    excluded.add(ln)
        return excluded

    def check(self, document: Document, config: MD012Config) -> list[Violation]:
        """Check for multiple consecutive blank lines."""
        violations: list[Violation] = []

        maximum = config.maximum
        excluded_lines = self._get_excluded_lines(document)

        # Track consecutive blank line count
        blank_count = 0

        for line_num, line in enumerate(document.lines, start=1):
            in_excluded = line_num in excluded_lines

            # Reset count if in excluded region or line has content
            if in_excluded or line.strip():
                blank_count = 0
                continue

            # Line is blank and not in excluded region
            blank_count += 1

            if blank_count > maximum:
                violations.append(
                    Violation(
                        line=line_num,
                        column=1,
                        rule_id=self.id,
                        rule_name=self.name,
                        message=(
                            f"Expected at most {maximum} consecutive blank "
                            f"lines, found {blank_count}"
                        ),
                        context=None,
                    )
                )

        return violations

    def fix(self, document: Document, config: MD012Config) -> str | None:
        """Fix multiple consecutive blank lines by collapsing them to the maximum allowed."""
        maximum = config.maximum

        excluded_lines = self._get_excluded_lines(document)

        lines = document.content.split("\n")
        result: list[str] = []
        blank_count = 0
        changed = False
        num_lines = len(document.lines)

        for line_num, line in enumerate(lines, start=1):
            if line_num > num_lines:
                # Preserve trailing element from split("\n") that is beyond
                # the actual document lines (artifact of trailing newline)
                result.append(line)
                continue

            in_excluded = line_num in excluded_lines

            if in_excluded or line.strip():
                blank_count = 0
                result.append(line)
                continue

            blank_count += 1

            if blank_count > maximum:
                changed = True
                continue

            result.append(line)

        if not changed:
            return None

        return "\n".join(result)
