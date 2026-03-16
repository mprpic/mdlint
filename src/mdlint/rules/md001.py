import re
from dataclasses import dataclass, field

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD001Config(RuleConfig):
    """Configuration for MD001 rule."""

    front_matter_title: str = field(
        default=r"^\s*title\s*[:=]",
        metadata={
            "description": (
                "Regex pattern to match title in front matter. If front matter "
                "contains a matching line, it is treated as an implicit h1. Set to "
                "empty string to disable."
            ),
        },
    )


class MD001(Rule[MD001Config]):
    """Heading levels should only increment by one level at a time."""

    id = "MD001"
    name = "heading-increment"
    summary = "Heading levels should only increment by one level at a time"
    config_class = MD001Config

    description = (
        "This rule checks that heading levels increment sequentially without "
        "skipping levels. For example, an h1 should be followed by an h2, not "
        "directly by an h3 or h4. Both ATX-style headings (using `#` characters) "
        "and setext-style headings (using underlines with `=` or `-`) are checked."
    )

    rationale = (
        "Headings represent the structure of a document and can be confusing "
        "when skipped, especially for accessibility scenarios. Screen readers "
        "and other assistive technologies rely on proper heading hierarchy to "
        "accurately convey the document's structure. If front matter contains "
        "a title (matched by the `front_matter_title` regex), it is treated as "
        "an implicit h1, so the first heading in the document should be h2. "
        "Set `front_matter_title` to an empty string to disable this behavior."
    )

    example_valid = """\
# Heading 1

## Heading 2

### Heading 3

#### Heading 4

## Another Heading 2

### Another Heading 3
"""

    example_invalid = """\
# Heading 1

### Heading 3

###### Heading 6
"""

    def check(self, document: Document, config: MD001Config) -> list[Violation]:
        """Check for heading increment violations."""
        violations: list[Violation] = []

        # Check if front matter contains a title (treated as implicit h1)
        prev_level: int | None = None
        if (
            config.front_matter_title
            and document.front_matter
            and re.search(config.front_matter_title, document.front_matter, re.MULTILINE)
        ):
            prev_level = 1

        for token in document.tokens:
            if token.type == "heading_open":
                # Extract level from tag (h1 -> 1, h2 -> 2, etc.)
                level = int(token.tag[1])
                line = token.map[0] + 1 if token.map else 1

                if prev_level is not None and level > prev_level + 1:
                    context = document.get_line(line)
                    violations.append(
                        Violation(
                            line=line,
                            column=1,
                            rule_id=self.id,
                            rule_name=self.name,
                            message=(
                                f"Heading level increased from h{prev_level} to h{level}, "
                                f"expected h{prev_level + 1}"
                            ),
                            context=context,
                        )
                    )

                prev_level = level

        return violations

    def fix(self, document: Document, config: MD001Config) -> str | None:
        """Fix heading increment violations by adjusting heading levels."""
        # Collect heading info: (token_index, line_0indexed, current_level, token_tag)
        headings: list[tuple[int, int, int, str]] = []
        for i, token in enumerate(document.tokens):
            if token.type == "heading_open":
                level = int(token.tag[1])
                line = token.map[0] if token.map else 0
                headings.append((i, line, level, token.tag))

        if not headings:
            return None

        # Determine the expected level for each heading
        prev_level: int | None = None
        if (
            config.front_matter_title
            and document.front_matter
            and re.search(config.front_matter_title, document.front_matter, re.MULTILINE)
        ):
            prev_level = 1

        adjustments: list[tuple[int, int, int]] = []  # (line_0indexed, old_level, new_level)
        for _, line, level, _ in headings:
            if prev_level is not None and level > prev_level + 1:
                new_level = prev_level + 1
                adjustments.append((line, level, new_level))
                prev_level = new_level
            else:
                prev_level = level

        if not adjustments:
            return None

        lines = document.content.split("\n")
        for line_idx, _, new_level in reversed(adjustments):
            line = lines[line_idx]
            # ATX heading: starts with # characters
            atx_match = re.match(r"^(#{1,6})(\s)", line)
            if atx_match:
                lines[line_idx] = "#" * new_level + line[len(atx_match.group(1)) :]
            else:
                # Setext heading: the underline is on the next line
                # Setext h1 uses ===, h2 uses ---
                # If new_level <= 2, keep setext style; otherwise convert to ATX
                if new_level <= 2:
                    underline_char = "=" if new_level == 1 else "-"
                    underline_line = line_idx + 1
                    if underline_line < len(lines):
                        old_underline = lines[underline_line]
                        lines[underline_line] = underline_char * len(old_underline)
                else:
                    # Convert setext to ATX
                    heading_text = line
                    lines[line_idx] = "#" * new_level + " " + heading_text
                    # Remove the underline
                    underline_line = line_idx + 1
                    if underline_line < len(lines):
                        lines.pop(underline_line)

        return "\n".join(lines)
