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
        default=False,
        metadata={
            "description": (
                "Whether to check code blocks and inline code spans for trailing "
                "spaces. When False (default), fenced code blocks, indented code "
                "blocks, and whitespace inside inline code spans that wrap onto "
                "the next line are ignored, since that whitespace is code content "
                "and some programming languages require it. When True, they are "
                "checked and fixed like any other line."
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
        "exceptions for intentional line breaks (typically 2 spaces). Code "
        "blocks and inline code spans are skipped unless `code_blocks` is "
        "enabled, and front matter is never checked."
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
        code_span_positions: dict[int, set[int]] = {}
        if not config.code_blocks:
            code_block_lines = document.code_block_lines
            code_span_positions = document.code_span_positions
        front_matter_lines = document.front_matter_lines

        results: list[tuple[int, str, int]] = []
        for line_num, line in enumerate(document.lines, start=1):
            if line_num in code_block_lines or line_num in front_matter_lines:
                continue

            stripped = line.rstrip()
            trailing_count = len(line) - len(stripped)

            if trailing_count == 0:
                continue

            # The whitespace belongs to a code span that continues on the next line
            if len(stripped) + 1 in code_span_positions.get(line_num, set()):
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

    @staticmethod
    def _hard_break_lines(document: Document) -> set[int]:
        """1-indexed lines whose trailing spaces would render a hard line break.

        That is every line of a paragraph but its last, unless the spaces are inside a code
        span that continues on the next line.
        """
        lines: set[int] = set()
        for token in document.tokens:
            if token.type == "inline" and token.map:
                for line_num in range(token.map[0] + 1, token.map[1]):
                    line = document.get_line(line_num) or ""
                    end = len(line.rstrip()) + 1
                    if end not in document.code_span_positions.get(line_num, set()):
                        lines.add(line_num)
        return lines

    def fix(self, document: Document, config: MD009Config) -> str | None:
        """Fix trailing spaces by removing them.

        Two or more trailing spaces after text render as a hard line break, so there the
        whitespace is trimmed to exactly `br_spaces` spaces instead, keeping the break.
        """
        violating_lines = self._get_violating_lines(document, config)
        if not violating_lines:
            return None

        break_lines = self._hard_break_lines(document) if config.br_spaces >= 2 else set()
        lines = document.content.split("\n")
        for line_num, stripped, _ in violating_lines:
            hard_break = line_num in break_lines and lines[line_num - 1].endswith("  ")
            lines[line_num - 1] = stripped + " " * config.br_spaces if hard_break else stripped

        return "\n".join(lines)
