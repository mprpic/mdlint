from dataclasses import dataclass, field

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD009Config(RuleConfig):
    """Configuration for MD009 rule."""

    br_spaces: int = field(
        default=2,
        metadata={
            "description": (
                "Number of trailing spaces to allow for hard line breaks. When set "
                "to 2 or higher, lines ending with exactly this many spaces (preceded "
                "by a non-whitespace character) are allowed as they create <br> "
                "elements. Setting to 0 or 1 disables this exception."
            ),
        },
    )
    code_blocks: bool = field(
        default=True,
        metadata={
            "description": (
                "Whether to check code blocks for trailing spaces. When True "
                "(default), code blocks are checked. When False, fenced and "
                "indented code blocks are ignored, since some programming "
                "languages require trailing whitespace."
            ),
        },
    )


class MD009(Rule[MD009Config]):
    """No trailing spaces."""

    id = "MD009"
    name = "no-trailing-spaces"
    summary = "No trailing spaces"
    config_class = MD009Config

    description = (
        "This rule detects trailing whitespace at the end of lines. It "
        "triggers on any lines that end with unexpected whitespace, with "
        "exceptions for intentional line breaks (typically 2 spaces)."
    )

    rationale = (
        "Except when used to create a line break, trailing whitespace has "
        "no purpose and does not affect rendering. Trailing spaces create "
        "unnecessary clutter in source files and can cause inconsistencies "
        "across different editors and version control systems."
    )

    def check(self, document: Document, config: MD009Config) -> list[Violation]:
        """Check for trailing spaces violations."""
        violations: list[Violation] = []

        br_spaces = config.br_spaces

        # Build set of line numbers inside code blocks if configured to skip them
        code_block_lines: set[int] = set()
        if not config.code_blocks:
            code_block_lines = self._get_code_block_lines(document)

        for line_num, line in enumerate(document.lines, start=1):
            if line_num in code_block_lines:
                continue

            # Calculate trailing whitespace count
            stripped = line.rstrip()
            trailing_count = len(line) - len(stripped)

            if trailing_count == 0:
                continue

            # Check if this is an allowed hard break
            # Hard break requires: br_spaces >= 2, exactly br_spaces trailing spaces,
            # and a non-whitespace character before the trailing spaces
            is_valid_hard_break = (
                br_spaces >= 2
                and trailing_count == br_spaces
                and len(stripped) > 0
                and not stripped[-1].isspace()
            )

            if is_valid_hard_break:
                continue

            # This is a violation
            # Column points to first trailing whitespace (1-indexed)
            column = len(stripped) + 1

            violations.append(
                Violation(
                    line=line_num,
                    column=column,
                    rule_id=self.id,
                    rule_name=self.name,
                    message=(
                        f"Trailing whitespace found "
                        f"({trailing_count} character{'s' if trailing_count != 1 else ''})"
                    ),
                    context=line,
                )
            )

        return violations
