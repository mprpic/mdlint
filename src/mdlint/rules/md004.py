from dataclasses import dataclass, field
from typing import Literal

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD004Config(RuleConfig):
    """Configuration for MD004 rule."""

    ListStyle = Literal["asterisk", "plus", "dash", "sublist", "consistent"]

    style: ListStyle = field(
        default="consistent",
        metadata={
            "description": "Required list marker style.",
            "option_descriptions": {
                "consistent": "All list markers in the document must match the first one used",
                "asterisk": "All list markers must be *",
                "plus": "All list markers must be +",
                "dash": "All list markers must be -",
                "sublist": (
                    "Each nesting level must use the same marker style throughout the document"
                ),
            },
        },
    )


class MD004(Rule[MD004Config]):
    """Unordered list style should be consistent."""

    id = "MD004"
    name = "ul-style"
    summary = "Unordered list style should be consistent"
    config_class = MD004Config

    description = (
        "This rule ensures that unordered list markers throughout a document "
        "follow a consistent style. It validates that bullet points use "
        "matching symbols (asterisks, plus signs, or dashes) according to "
        "the configured preference. In ``consistent`` mode, all list markers "
        "across the entire document must match the first one used, even "
        "across separate lists. In ``sublist`` mode, each nesting level must "
        "use the same marker style throughout the document."
    )

    rationale = (
        "Consistent formatting makes it easier to understand a document. "
        "Uniform list styling promotes readability and professional "
        "presentation, reducing cognitive friction when reading list content."
    )

    example_valid = """\
# Consistent List Markers

- Item 1
- Item 2
- Item 3
  - Nested item 1
  - Nested item 2
- Item 4
"""

    example_invalid = """\
# Mixed List Markers

- Item with dash
* Item with asterisk
+ Item with plus
"""

    MARKER_TO_STYLE = {
        "*": "asterisk",
        "+": "plus",
        "-": "dash",
    }

    def check(self, document: Document, config: MD004Config) -> list[Violation]:
        """Check for list marker consistency."""
        violations: list[Violation] = []

        style = config.style

        # Track expected style (for consistent mode)
        expected_style: str | None = None
        if style in ("asterisk", "plus", "dash"):
            expected_style = style

        # Track style per nesting level (for sublist mode)
        level_styles: dict[int, str] = {}
        current_level = 0

        for token in document.tokens:
            # Track nesting level
            if token.type == "bullet_list_open":
                current_level += 1
            elif token.type == "bullet_list_close":
                current_level = max(0, current_level - 1)
            elif token.type == "list_item_open" and token.markup in self.MARKER_TO_STYLE:
                line = token.map[0] + 1 if token.map else 1
                current_marker_style = self.MARKER_TO_STYLE[token.markup]

                if style == "sublist":
                    # Each level has its own expected style
                    if current_level not in level_styles:
                        level_styles[current_level] = current_marker_style
                    elif level_styles[current_level] != current_marker_style:
                        context = document.get_line(line)
                        violations.append(
                            Violation(
                                line=line,
                                column=1,
                                rule_id=self.id,
                                rule_name=self.name,
                                message=(
                                    f"List marker style at level {current_level}: "
                                    f"expected {level_styles[current_level]}, "
                                    f"found {current_marker_style}"
                                ),
                                context=context,
                            )
                        )
                else:
                    # Consistent or fixed style
                    if expected_style is None:
                        expected_style = current_marker_style
                    elif current_marker_style != expected_style:
                        context = document.get_line(line)
                        violations.append(
                            Violation(
                                line=line,
                                column=1,
                                rule_id=self.id,
                                rule_name=self.name,
                                message=(
                                    f"List marker style: expected {expected_style}, "
                                    f"found {current_marker_style}"
                                ),
                                context=context,
                            )
                        )

        return violations

    STYLE_TO_MARKER = {
        "asterisk": "*",
        "plus": "+",
        "dash": "-",
    }

    def fix(self, document: Document, config: MD004Config) -> str | None:
        """Fix list marker style violations by replacing markers with the expected style."""
        style = config.style

        # Collect list item info: (line_0indexed, current_marker, nesting_level)
        items: list[tuple[int, str, int]] = []
        current_level = 0

        for token in document.tokens:
            if token.type == "bullet_list_open":
                current_level += 1
            elif token.type == "bullet_list_close":
                current_level = max(0, current_level - 1)
            elif token.type == "list_item_open" and token.markup in self.MARKER_TO_STYLE:
                line_0 = token.map[0] if token.map else 0
                items.append((line_0, token.markup, current_level))

        if not items:
            return None

        # Determine expected marker for each item
        level_styles: dict[int, str] = {}
        expected_style: str | None = None
        if style == "sublist":
            for _, marker, level in items:
                if level not in level_styles:
                    level_styles[level] = self.MARKER_TO_STYLE[marker]
        elif style in ("asterisk", "plus", "dash"):
            expected_style = style
        else:
            # consistent: use first marker's style
            expected_style = self.MARKER_TO_STYLE[items[0][1]]

        # Build list of fixes: (line_0indexed, expected_marker)
        fixes: list[tuple[int, str]] = []
        for line_0, marker, level in items:
            current_marker_style = self.MARKER_TO_STYLE[marker]
            if style == "sublist":
                exp = level_styles[level]
            else:
                assert expected_style is not None
                exp = expected_style

            if current_marker_style != exp:
                fixes.append((line_0, self.STYLE_TO_MARKER[exp]))

        if not fixes:
            return None

        lines = document.content.split("\n")
        for line_0, new_marker in fixes:
            line = lines[line_0]
            # Find the first list marker (-, *, +) preceded only by whitespace/blockquote chars
            for i, ch in enumerate(line):
                if ch in "-*+" and i + 1 < len(line) and line[i + 1] == " ":
                    lines[line_0] = line[:i] + new_marker + line[i + 1 :]
                    break
                if ch not in " \t>":
                    break

        return "\n".join(lines)
