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
