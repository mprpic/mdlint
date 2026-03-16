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

                # Determine the effective expected style for this heading level
                if expected_style in ("setext_with_atx", "setext_with_atx_closed"):
                    atx_variant = "atx" if expected_style == "setext_with_atx" else "atx_closed"
                    effective_expected = "setext" if level <= 2 else atx_variant
                else:
                    effective_expected = expected_style

                if current_style != effective_expected:
                    context = document.get_line(line)
                    violations.append(
                        Violation(
                            line=line,
                            column=1,
                            rule_id=self.id,
                            rule_name=self.name,
                            message=f"Expected {effective_expected}, found {current_style}",
                            context=context,
                        )
                    )

        return violations

    def fix(self, document: Document, config: MD003Config) -> str | None:
        """Fix heading style violations by converting headings to the expected style."""
        style = config.style
        expected_style: str | None = None if style == "consistent" else style

        # Collect heading info: (line_0indexed, level, current_style)
        headings: list[tuple[int, int, str]] = []
        for token in document.tokens:
            if token.type == "heading_open":
                level = int(token.tag[1])
                line_0 = token.map[0] if token.map else 0
                raw_line = document.get_line(line_0 + 1)
                current_style = self._get_heading_style(token.markup, raw_line)
                headings.append((line_0, level, current_style))

        if not headings:
            return None

        # For consistent mode, determine expected from first heading
        if expected_style is None:
            expected_style = headings[0][2]

        # Determine which headings need fixing
        # (line_0idx, level, current_style, effective_expected)
        fixes: list[tuple[int, int, str, str]] = []
        for line_0, level, current_style in headings:
            if expected_style in ("setext_with_atx", "setext_with_atx_closed"):
                atx_variant = "atx" if expected_style == "setext_with_atx" else "atx_closed"
                effective_expected = "setext" if level <= 2 else atx_variant
            else:
                effective_expected = expected_style

            if current_style != effective_expected:
                # Skip impossible conversions: can't convert h3+ to setext
                if effective_expected == "setext" and level > 2:
                    continue
                fixes.append((line_0, level, current_style, effective_expected))

        if not fixes:
            return None

        lines = document.content.split("\n")

        # Process fixes in reverse order to preserve line indices
        for line_0, level, current, target in reversed(fixes):
            raw_line = lines[line_0]

            if current == "setext":
                # Heading text is on this line, underline is next line
                heading_text = raw_line
                underline_idx = line_0 + 1

                if target == "atx":
                    lines[line_0] = "#" * level + " " + heading_text
                    if underline_idx < len(lines):
                        lines.pop(underline_idx)
                elif target == "atx_closed":
                    lines[line_0] = "#" * level + " " + heading_text + " " + "#" * level
                    if underline_idx < len(lines):
                        lines.pop(underline_idx)

            elif current == "atx":
                heading_text = re.sub(r"^#{1,6}\s+", "", raw_line)

                if target == "setext":
                    underline_char = "=" if level == 1 else "-"
                    lines[line_0] = heading_text
                    lines.insert(line_0 + 1, underline_char * len(heading_text))
                elif target == "atx_closed":
                    lines[line_0] = "#" * level + " " + heading_text + " " + "#" * level

            elif current == "atx_closed":
                heading_text = re.sub(r"^#{1,6}\s+", "", raw_line)
                heading_text = re.sub(r"\s+#{1,6}\s*$", "", heading_text)

                if target == "setext":
                    underline_char = "=" if level == 1 else "-"
                    lines[line_0] = heading_text
                    lines.insert(line_0 + 1, underline_char * len(heading_text))
                elif target == "atx":
                    lines[line_0] = "#" * level + " " + heading_text

        return "\n".join(lines)
