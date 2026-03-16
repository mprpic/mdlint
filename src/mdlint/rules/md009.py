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

    @staticmethod
    def _is_valid_hard_break(br_spaces: int, trailing_count: int, stripped: str) -> bool:
        """Check if trailing spaces represent a valid hard line break."""
        return (
            br_spaces >= 2
            and trailing_count == br_spaces
            and len(stripped) > 0
            and not stripped[-1].isspace()
        )

    def _get_violating_lines(
        self, document: Document, config: MD009Config
    ) -> list[tuple[int, str, int]]:
        """Return list of (line_num, stripped_line, trailing_count) for violating lines."""
        br_spaces = config.br_spaces

        code_block_lines: set[int] = set()
        if not config.code_blocks:
            code_block_lines = document.code_block_lines

        results: list[tuple[int, str, int]] = []
        for line_num, line in enumerate(document.lines, start=1):
            if line_num in code_block_lines:
                continue

            stripped = line.rstrip()
            trailing_count = len(line) - len(stripped)

            if trailing_count == 0:
                continue

            if not self._is_valid_hard_break(br_spaces, trailing_count, stripped):
                results.append((line_num, stripped, trailing_count))

        return results

    def check(self, document: Document, config: MD009Config) -> list[Violation]:
        """Check for trailing spaces violations."""
        violations: list[Violation] = []

        for line_num, stripped, trailing_count in self._get_violating_lines(document, config):
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
                    context=document.get_line(line_num),
                )
            )

        return violations

    def fix(self, document: Document, config: MD009Config) -> str | None:
        """Fix trailing spaces by removing them."""
        violating_lines = self._get_violating_lines(document, config)
        if not violating_lines:
            return None

        lines = document.content.split("\n")
        for line_num, stripped, _ in violating_lines:
            lines[line_num - 1] = stripped

        return "\n".join(lines)
