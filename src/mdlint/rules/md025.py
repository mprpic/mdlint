from dataclasses import dataclass, field

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD025Config(RuleConfig):
    """Configuration for MD025 rule."""

    level: int = field(
        default=1,
        metadata={
            "description": "Heading level to treat as top-level (1-6). Default is 1 (h1).",
        },
    )


class MD025(Rule[MD025Config]):
    """Multiple top-level headings in the same document."""

    id = "MD025"
    name = "single-title"
    summary = "Multiple top-level headings in the same document"
    config_class = MD025Config

    description = (
        "This rule checks that only one top-level heading (h1 by default) "
        "exists in a document. It triggers when multiple h1 headings are "
        "found, as only one should serve as the document title. The `level` "
        "parameter can be used to change the top-level heading (e.g. to h2) "
        "in cases where an h1 is added externally by the rendering platform."
    )

    rationale = (
        "A top-level heading serves as the title for the document. If this "
        "convention is followed, there should only be one title, and the "
        "entire document should be contained within it. Having multiple "
        "top-level headings breaks document hierarchy and can confuse "
        "readers and tools that generate tables of contents."
    )

    example_valid = """\
# Document Title

## First Section

Some content here.

## Second Section

More content here.
"""

    example_invalid = """\
# First Title

Some content.

# Second Title

This document has multiple top-level headings.
"""

    def check(self, document: Document, config: MD025Config) -> list[Violation]:
        """Check for multiple top-level headings."""
        violations: list[Violation] = []
        target_level = config.level
        found_top_level = False
        blockquote_depth = 0

        for token in document.tokens:
            if token.type == "blockquote_open":
                blockquote_depth += 1
            elif token.type == "blockquote_close":
                blockquote_depth -= 1
            elif token.type == "heading_open" and blockquote_depth == 0:
                level = int(token.tag[1])

                if level == target_level:
                    if found_top_level:
                        line = token.map[0] + 1 if token.map else 1
                        context = document.get_line(line)
                        violations.append(
                            Violation(
                                line=line,
                                column=1,
                                rule_id=self.id,
                                rule_name=self.name,
                                message=f"Multiple h{target_level} headings found",
                                context=context,
                            )
                        )
                    else:
                        found_top_level = True

        return violations
