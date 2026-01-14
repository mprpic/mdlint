import re
from dataclasses import dataclass, field

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD026Config(RuleConfig):
    """Configuration for MD026 rule."""

    punctuation: str = field(
        default=".,;:!",
        metadata={
            "description": "Characters considered as trailing punctuation.",
        },
    )


class MD026(Rule[MD026Config]):
    """Trailing punctuation in heading."""

    id = "MD026"
    name = "no-trailing-punctuation"
    summary = "Trailing punctuation in heading"
    config_class = MD026Config

    CLOSING_ATX_RE = re.compile(r"\s+#+\s*$")
    HTML_ENTITY_RE = re.compile(r"&(?:#[xX]?[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]*);$")

    description = (
        "This rule checks that headings do not end with punctuation characters. "
        "By default, it flags periods, commas, semicolons, colons, and exclamation marks. "
        "Question marks are allowed by default since they are common in FAQ-style headings."
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

    def check(self, document: Document, config: MD026Config) -> list[Violation]:
        """Check for trailing punctuation in headings."""
        violations: list[Violation] = []

        if not config.punctuation:
            return violations

        for token in document.tokens:
            if token.type == "heading_open" and token.map:
                line_num = token.map[0] + 1
                line_content = document.get_line(line_num)

                if line_content is None:
                    continue

                stripped = line_content.rstrip()

                # Strip closing ATX hash sequences (e.g. "## Heading ##")
                if token.markup not in ("=", "-"):
                    closing_match = self.CLOSING_ATX_RE.search(stripped)
                    if closing_match:
                        stripped = stripped[: closing_match.start()]

                # Get heading text by stripping ATX markers and whitespace
                heading_text = stripped.lstrip("#").strip()

                # Handle setext headings - the text is on the line itself
                if not heading_text and token.markup in ("=", "-"):
                    heading_text = stripped.strip()

                if not heading_text:
                    continue

                last_char = heading_text[-1]
                if last_char in config.punctuation:
                    # Skip HTML entity references ending with semicolon
                    if last_char == ";" and self.HTML_ENTITY_RE.search(heading_text):
                        continue

                    column = len(stripped)
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
