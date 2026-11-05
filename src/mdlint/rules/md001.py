import re
from dataclasses import dataclass, field

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD001Config(RuleConfig):
    """Configuration for MD001 rule."""

    front_matter_title: str = field(
        default=r"^title\s*[:=]",
        metadata={
            "regex": True,
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

    ATX_OPENING_RE = re.compile(r"[ \t]*(#{1,6})")

    description = (
        "This rule checks that heading levels increment sequentially without "
        "skipping levels. For example, an h1 should be followed by an h2, not "
        "directly by an h3 or h4. Both ATX-style headings (using `#` characters) "
        "and setext-style headings (using underlines with `=` or `-`) are checked. "
        "When fixing, the headings that follow a skipped level move up with it, so "
        "`# A`, `### B`, `#### C` becomes `# A`, `## B`, `### C`."
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
        """Fix heading increment violations by adjusting heading levels.

        Headings after an offender move with it: each heading ends up one level below the
        nearest earlier heading of a lower original level. Moving only the offender would
        turn ``# A/### B/#### C/### D`` into ``# A/## B/### C/### D``, making D a child of B.
        Setext headings never change, since an h1 or h2 can never skip a level.
        """
        # (original level, new level) of the headings that enclose the current position
        open_headings: list[tuple[int, int]] = []
        if (
            config.front_matter_title
            and document.front_matter
            and re.search(config.front_matter_title, document.front_matter, re.MULTILINE)
        ):
            open_headings.append((1, 1))

        changes: list[tuple[int, int]] = []  # (line_0indexed, new_level)
        for token in document.tokens:
            if token.type != "heading_open" or not token.map:
                continue
            level = int(token.tag[1])
            while open_headings and open_headings[-1][0] >= level:
                open_headings.pop()
            new_level = open_headings[-1][1] + 1 if open_headings else level
            open_headings.append((level, new_level))
            if new_level != level:
                changes.append((token.map[0], new_level))

        if not changes:
            return None

        lines = document.content.split("\n")
        for line_idx, new_level in changes:
            line = lines[line_idx]
            # Skip blockquote markers and list indentation so only the opening hashes change.
            match = self.ATX_OPENING_RE.match(line, len(document.container_prefix(line_idx + 1)))
            if match:
                lines[line_idx] = line[: match.start(1)] + "#" * new_level + line[match.end(1) :]

        return "\n".join(lines)
