from dataclasses import dataclass, field
from typing import Literal

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
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

        for token in document.tokens:
            if token.type != "inline" or not token.children or not token.map:
                continue

            base_line = token.map[0] + 1
            search_pos = 0

            for child in token.children:
                # Advance past non-strong tokens to keep search_pos correct
                if child.type in ("strong_close", "em_open", "em_close") and child.markup:
                    pos = token.content.find(child.markup, search_pos)
                    if pos >= 0:
                        search_pos = pos + len(child.markup)
                    continue

                if child.type == "text" and child.content:
                    pos = token.content.find(child.content, search_pos)
                    if pos >= 0:
                        search_pos = pos + len(child.content)
                    continue

                if child.type == "softbreak":
                    pos = token.content.find("\n", search_pos)
                    if pos >= 0:
                        search_pos = pos + 1
                    continue

                if child.type == "code_inline" and child.markup:
                    pos = token.content.find(child.markup, search_pos)
                    if pos >= 0:
                        search_pos = pos + len(child.markup) * 2 + len(child.content)
                    continue

                if child.type != "strong_open":
                    continue

                marker = child.markup
                if marker not in self.MARKUP_TO_STYLE:
                    continue

                line, column, search_pos = self._find_marker_position(
                    token.content, marker, search_pos, base_line
                )

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

    @staticmethod
    def _find_marker_position(
        content: str, marker: str, search_pos: int, base_line: int
    ) -> tuple[int, int, int]:
        """Find line and column of a marker in raw inline content."""
        pos = content.find(marker, search_pos)
        if pos < 0:
            return base_line, 1, search_pos

        text_before = content[:pos]
        line_offset = text_before.count("\n")
        last_nl = text_before.rfind("\n")
        column = pos - last_nl  # 1-indexed (rfind returns -1 when no \n)

        return base_line + line_offset, column, pos + len(marker)
