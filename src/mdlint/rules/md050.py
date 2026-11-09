from dataclasses import dataclass, field
from typing import Literal

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.rules.md049 import emphasis_marker_positions
from mdlint.violation import Violation


@dataclass
class MD050Config(RuleConfig):
    """Configuration for MD050 rule."""

    StrongStyle = Literal["asterisk", "consistent", "underscore"]

    style: StrongStyle = field(
        default="consistent",
        metadata={
            "description": "Required strong/bold style.",
            "option_descriptions": {
                "consistent": "All strong markers must match the first one used",
                "asterisk": "All strong markers must use `**`",
                "underscore": "All strong markers must use `__`",
            },
        },
    )


class MD050(Rule[MD050Config]):
    """Strong style should be consistent."""

    id = "MD050"
    name = "strong-style"
    summary = "Strong style should be consistent"
    config_class = MD050Config
    preserves_rendering = True

    description = (
        "This rule is triggered when the symbols used in the document for "
        "strong/bold text do not match the configured style. Markdown supports "
        "both double asterisks (`**text**`) and double underscores (`__text__`) for "
        "strong emphasis."
    )

    rationale = (
        "Consistent formatting makes it easier to understand a document. Using "
        "the same strong emphasis style throughout a document improves readability."
    )

    example_valid = """\
# Consistent Strong Style

This text uses **asterisks** for bold.

Another **bold word** in the document.

Multiple **bold** words on the **same** line.
"""

    example_invalid = """\
# Inconsistent Strong Style

This text uses **asterisks** for bold.

But this uses __underscores__ for bold.
"""

    MARKUP_TO_STYLE = {
        "**": "asterisk",
        "__": "underscore",
    }

    def check(self, document: Document, config: MD050Config) -> list[Violation]:
        """Check for strong style consistency."""
        violations: list[Violation] = []

        expected_style: str | None = None
        if config.style in ("asterisk", "underscore"):
            expected_style = config.style

        line_cursors: dict[int, int] = {}

        for token in document.tokens:
            if token.type != "inline" or not token.children or not token.map:
                continue

            positions = emphasis_marker_positions(document, token, line_cursors)

            for i, child in enumerate(token.children):
                if child.type != "strong_open":
                    continue

                marker = child.markup
                if marker not in self.MARKUP_TO_STYLE:
                    continue

                line, column = positions.get(i, (token.map[0] + 1, 1))

                current_style = self.MARKUP_TO_STYLE[marker]

                if expected_style is None:
                    expected_style = current_style
                elif current_style != expected_style:
                    violations.append(
                        Violation(
                            line=line,
                            column=column,
                            rule_id=self.id,
                            rule_name=self.name,
                            message=(
                                f"Strong style: expected {expected_style}, found {current_style}"
                            ),
                            context=document.get_line(line),
                        )
                    )

        return violations

    def fix(self, document: Document, config: MD050Config) -> str | None:
        """Fix strong style by replacing markers to match expected style."""
        expected_style: str | None = None
        if config.style in ("asterisk", "underscore"):
            expected_style = config.style

        # For "consistent" mode, determine style from first strong marker
        if expected_style is None:
            for token in document.tokens:
                if token.type != "inline" or not token.children:
                    continue
                for child in token.children:
                    if child.type == "strong_open" and child.markup in self.MARKUP_TO_STYLE:
                        expected_style = self.MARKUP_TO_STYLE[child.markup]
                        break
                if expected_style:
                    break

        if expected_style is None:
            return None

        target_marker = "**" if expected_style == "asterisk" else "__"

        # Collect (line_1indexed, column_1indexed) positions of markers to replace
        replacements: list[tuple[int, int]] = []
        line_cursors: dict[int, int] = {}

        for token in document.tokens:
            if token.type != "inline" or not token.children or not token.map:
                continue

            positions = emphasis_marker_positions(document, token, line_cursors)
            # Opener position of each open strong if it should be fixed, None otherwise
            fix_stack: list[tuple[int, int] | None] = []

            for i, child in enumerate(token.children):
                if child.type == "strong_open":
                    marker = child.markup
                    if marker not in self.MARKUP_TO_STYLE:
                        continue

                    position = positions.get(i)
                    should_fix = self.MARKUP_TO_STYLE[marker] != expected_style
                    fix_stack.append(position if should_fix else None)
                    continue

                if child.type == "strong_close":
                    marker = child.markup
                    if marker not in self.MARKUP_TO_STYLE:
                        continue

                    open_position = fix_stack.pop() if fix_stack else None
                    close_position = positions.get(i)
                    # Rewrite both markers or neither, so a pair is never left mismatched
                    if open_position is not None and close_position is not None:
                        replacements.extend((open_position, close_position))
                    continue

        if not replacements:
            return None

        lines = document.content.split("\n")
        for line_num, column in sorted(replacements, reverse=True):
            line_idx = line_num - 1
            col_idx = column - 1
            line = lines[line_idx]
            lines[line_idx] = line[:col_idx] + target_marker + line[col_idx + 2 :]

        return "\n".join(lines)
