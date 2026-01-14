import re
from dataclasses import dataclass, field
from typing import Literal

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD003Config(RuleConfig):
    """Configuration for MD003 rule."""

    HeadingStyle = Literal[
        "atx", "atx_closed", "setext", "setext_with_atx", "setext_with_atx_closed", "consistent"
    ]

    style: HeadingStyle = field(
        default="consistent",
        metadata={
            "description": "Required heading style.",
            "option_descriptions": {
                "consistent": "All headings must match the style of the first heading",
                "atx": "All headings must use ATX-style headings (using `#` character)",
                "atx_closed": "All headings must use ATX-style with a closing `#` character",
                "setext": "All headings must use underline style (only h1/h2)",
                "setext_with_atx": "h1/h2 use Setext-style headings, h3+ use atx",
                "setext_with_atx_closed": "h1/h2 use setext, h3+ use atx_closed",
            },
        },
    )


class MD003(Rule[MD003Config]):
    """Heading style should be consistent."""

    id = "MD003"
    name = "heading-style"
    summary = "Heading style should be consistent"
    config_class = MD003Config

    description = (
        "This rule enforces consistent heading styles throughout a document. "
        "It triggers when different heading formats are mixed, such as "
        "combining ATX-style headings (`#`) with Setext-style headings "
        "(underlined with `=` or `-`). The ``setext_with_atx`` and "
        "``setext_with_atx_closed`` modes allow mixed styles, requiring "
        "setext for h1/h2 and ATX (or ATX closed) for h3 and above. "
        "Note that a horizontal rule (``---``) directly below a line of "
        "text can be misinterpreted as a setext heading underline."
    )

    rationale = (
        "Consistent formatting makes it easier to understand a document. "
        "Mixing heading styles can be visually confusing and makes the "
        "source harder to maintain."
    )

    example_valid = """\
# ATX Heading 1

## ATX Heading 2

### ATX Heading 3

All headings use consistent ATX style.
"""

    example_invalid = """\
# ATX Heading 1

Setext Heading 2
----------------

### ATX Heading 3

Mixed heading styles in the same document.
"""

    @staticmethod
    def _get_heading_style(token_markup: str, raw_line: str | None) -> str:
        """Determine heading style from token markup and raw line content.

        Args:
            token_markup: The markup string from the token (e.g., "#", "##", "=", "-").
            raw_line: The raw line content from the source file.

        Returns:
            The heading style: "atx", "atx_closed", or "setext".
        """
        if token_markup.startswith("#"):
            # Check raw line for closing hashes (atx_closed style)
            if raw_line and re.search(r"\s#+\s*$", raw_line):
                return "atx_closed"
            return "atx"
        if token_markup in ("=", "-"):
            return "setext"
        return "atx"

    def check(self, document: Document, config: MD003Config) -> list[Violation]:
        """Check for heading style consistency."""
        violations: list[Violation] = []

        style = config.style
        expected_style: str | None = None if style == "consistent" else style

        for token in document.tokens:
            if token.type == "heading_open":
                level = int(token.tag[1])
                line = token.map[0] + 1 if token.map else 1
                raw_line = document.get_line(line)
                current_style = self._get_heading_style(token.markup, raw_line)

                # For consistent mode, set expected from first heading
                if expected_style is None:
                    expected_style = current_style
                    continue

                # Check style match
                is_violation = False

                if expected_style == "setext_with_atx":
                    # h1/h2 should be setext, h3+ should be atx
                    if level <= 2 and current_style != "setext":
                        is_violation = True
                    elif level > 2 and current_style != "atx":
                        is_violation = True
                elif expected_style == "setext_with_atx_closed":
                    # h1/h2 should be setext, h3+ should be atx_closed
                    if level <= 2 and current_style != "setext":
                        is_violation = True
                    elif level > 2 and current_style != "atx_closed":
                        is_violation = True
                elif current_style != expected_style:
                    is_violation = True

                if is_violation:
                    context = document.get_line(line)
                    # Use specific expected style in message for compound styles
                    if expected_style == "setext_with_atx":
                        display_expected = "setext" if level <= 2 else "atx"
                    elif expected_style == "setext_with_atx_closed":
                        display_expected = "setext" if level <= 2 else "atx_closed"
                    else:
                        display_expected = expected_style
                    violations.append(
                        Violation(
                            line=line,
                            column=1,
                            rule_id=self.id,
                            rule_name=self.name,
                            message=f"Expected {display_expected}, found {current_style}",
                            context=context,
                        )
                    )

        return violations
