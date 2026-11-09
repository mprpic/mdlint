import re
from dataclasses import dataclass, field
from pathlib import Path
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
    preserves_rendering = True

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

    @staticmethod
    def _reads_as_setext(text: str, level: int) -> bool:
        """Whether `text` over a setext underline parses back as the same heading."""
        underline = ("=" if level == 1 else "-") * len(text)
        tokens = Document(Path("<heading>"), f"{text}\n{underline}\n").tokens
        return (
            [token.type for token in tokens] == ["heading_open", "inline", "heading_close"]
            and tokens[0].tag == f"h{level}"
            and tokens[1].content == text
        )

    def fix(self, document: Document, config: MD003Config) -> str | None:
        """Fix heading style violations by converting headings to the expected style.

        A heading directly after paragraph or table text is left as is when it would become
        setext, because its text line would be absorbed into the block above. So is one whose
        text would start a block of its own, such as ``- item`` turning into a list item.
        """
        style = config.style
        expected_style: str | None = None if style == "consistent" else style

        # Lines on which a new line of text would continue the paragraph or table above
        absorbing_lines = {
            token.map[1]
            for token in document.tokens
            if token.type in ("paragraph_open", "table_open") and token.map
        }

        # Collect heading info: (line_0indexed, end_line_0indexed, level, current_style, text)
        headings: list[tuple[int, int, int, str, str]] = []
        for i, token in enumerate(document.tokens):
            if token.type == "heading_open" and token.map:
                level = int(token.tag[1])
                line_0, end_0 = token.map
                raw_line = document.get_line(line_0 + 1)
                current_style = self._get_heading_style(token.markup, raw_line)
                # The inline content has container markers and closing hashes removed.
                text = " ".join(part.strip() for part in document.tokens[i + 1].content.split("\n"))
                headings.append((line_0, end_0, level, current_style, text))

        if not headings:
            return None

        # For consistent mode, determine expected from first heading
        if expected_style is None:
            expected_style = headings[0][3]

        # Determine which headings need fixing
        # (line_0idx, end_0idx, level, current_style, effective_expected, text)
        fixes: list[tuple[int, int, int, str, str, str]] = []
        for line_0, end_0, level, current_style, text in headings:
            if expected_style in ("setext_with_atx", "setext_with_atx_closed"):
                atx_variant = "atx" if expected_style == "setext_with_atx" else "atx_closed"
                effective_expected = "setext" if level <= 2 else atx_variant
            else:
                effective_expected = expected_style

            if current_style != effective_expected:
                # Setext can't express h3+, an empty heading, a heading whose text line
                # would continue the paragraph or table above it, or text that would
                # start another kind of block.
                if effective_expected == "setext" and (
                    level > 2
                    or not text
                    or line_0 in absorbing_lines
                    or not self._reads_as_setext(text, level)
                ):
                    continue
                fixes.append((line_0, end_0, level, current_style, effective_expected, text))

        if not fixes:
            return None

        lines = document.content.split("\n")

        # Process fixes in reverse order to preserve line indices
        for line_0, end_0, level, _, target, text in reversed(fixes):
            prefix = document.container_prefix(line_0 + 1)

            if target == "setext":
                underline_char = "=" if level == 1 else "-"
                underline = document.continuation_prefix(line_0 + 1) + underline_char * len(text)
                lines[line_0:end_0] = [prefix + text, underline]
            else:
                marker = "#" * level
                closing = marker if target == "atx_closed" else ""
                heading = " ".join(part for part in (marker, text, closing) if part)
                # A setext heading spans its text lines and the underline.
                lines[line_0:end_0] = [prefix + heading]

        return "\n".join(lines)
