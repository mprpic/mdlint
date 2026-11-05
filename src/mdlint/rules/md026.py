import re
from dataclasses import dataclass, field

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD026Config(RuleConfig):
    """Configuration for MD026 rule."""

    punctuation: str = field(
        default=".,;:!。，；：！",
        metadata={
            "description": (
                "Characters considered as trailing punctuation. The default also "
                "includes the full-width forms used in CJK text."
            ),
        },
    )


class MD026(Rule[MD026Config]):
    """Trailing punctuation in heading."""

    id = "MD026"
    name = "no-trailing-punctuation"
    summary = "Trailing punctuation in heading"
    config_class = MD026Config

    ATX_OPENING_RE = re.compile(r"[ \t]*#{1,6}")
    CLOSING_ATX_RE = re.compile(r"\s+#+\s*$")
    HTML_ENTITY_RE = re.compile(r"&(?:#[xX]?[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]*);$")
    EMOJI_SHORTCODE_RE = re.compile(r"(?:^|\s):[\w+-]+:$")

    description = (
        "This rule checks that headings do not end with punctuation characters. "
        "By default, it flags periods, commas, semicolons, colons, and exclamation marks, "
        "including their full-width forms. Question marks are allowed by default since "
        "they are common in FAQ-style headings. A trailing HTML entity (`&copy;`) or "
        "emoji shortcode (`:rocket:`) is not punctuation."
    )

    rationale = (
        "Headings are not meant to be full sentences. Trailing punctuation "
        "in headings is unnecessary and inconsistent with most style guides."
    )

    example_valid = """\
# Heading without punctuation

## Another clean heading

### Question marks are allowed?

This document has proper headings.
"""

    example_invalid = """\
# Heading with period.

## Heading with colon:

### Heading with semicolon;

This document has headings with trailing punctuation.
"""

    def _strip_punctuation(self, text: str, punctuation: str) -> str:
        """Remove the whole trailing punctuation run, so one fix pass is enough."""
        while text and text[-1] in punctuation:
            # Entities and emoji shortcodes end in punctuation but render as one symbol.
            if text[-1] == ";" and self.HTML_ENTITY_RE.search(text):
                break
            if text[-1] == ":" and self.EMOJI_SHORTCODE_RE.search(text):
                break
            text = text[:-1].rstrip()
        return text

    def _find_trailing_punctuation(
        self, document: Document, config: MD026Config
    ) -> list[tuple[int, str, int, str, str | None]]:
        """Find headings with trailing punctuation.

        Returns list of (line_num, line_content, column, last_char, fixed_line) for each
        violating heading. ``fixed_line`` is None when removing the punctuation would leave
        the heading empty.
        """
        results: list[tuple[int, str, int, str, str | None]] = []

        if not config.punctuation:
            return results

        for token in document.tokens:
            if token.type == "heading_open" and token.map:
                setext = token.markup in ("=", "-")
                # A setext heading ends on the line above its underline.
                line_num = token.map[1] - 1 if setext else token.map[0] + 1
                line_content = document.get_line(line_num)

                if line_content is None:
                    continue

                stripped = line_content.rstrip()
                text_start = len(document.container_prefix(line_num))

                # Strip ATX markers, including closing hash sequences (e.g. "## Heading ##")
                closing_suffix = ""
                if not setext:
                    closing_match = self.CLOSING_ATX_RE.search(stripped)
                    if closing_match:
                        closing_suffix = stripped[closing_match.start() :]
                        stripped = stripped[: closing_match.start()]
                    opening_match = self.ATX_OPENING_RE.match(stripped, text_start)
                    if opening_match:
                        text_start = opening_match.end()

                heading_text = stripped[text_start:].strip()
                if not heading_text:
                    continue

                kept = self._strip_punctuation(heading_text, config.punctuation)
                if kept == heading_text:
                    continue

                fixed_line = None
                if kept:
                    trailing_ws = line_content[len(stripped) + len(closing_suffix) :]
                    head = stripped[: len(stripped) - len(heading_text)]
                    fixed_line = head + kept + closing_suffix + trailing_ws

                results.append(
                    (line_num, line_content, len(stripped), heading_text[-1], fixed_line)
                )

        return results

    def check(self, document: Document, config: MD026Config) -> list[Violation]:
        """Check for trailing punctuation in headings."""
        violations: list[Violation] = []

        for line_num, line_content, column, last_char, _ in self._find_trailing_punctuation(
            document, config
        ):
            violations.append(
                Violation(
                    line=line_num,
                    column=column,
                    rule_id=self.id,
                    rule_name=self.name,
                    message=f"Trailing punctuation '{last_char}' in heading",
                    context=line_content,
                )
            )

        return violations

    def fix(self, document: Document, config: MD026Config) -> str | None:
        """Fix trailing punctuation in headings by removing it."""
        fixes = [
            (line_num, fixed_line)
            for line_num, _, _, _, fixed_line in self._find_trailing_punctuation(document, config)
            if fixed_line is not None
        ]
        if not fixes:
            return None

        lines = document.content.split("\n")

        for line_num, fixed_line in fixes:
            lines[line_num - 1] = fixed_line

        return "\n".join(lines)
