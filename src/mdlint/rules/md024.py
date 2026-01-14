from dataclasses import dataclass, field

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD024Config(RuleConfig):
    """Configuration for MD024 rule."""

    siblings_only: bool = field(
        default=False,
        metadata={
            "description": (
                "When True, only flag duplicate headings within the same section "
                "(siblings). When False, all duplicate headings are flagged "
                "regardless of their position in the document hierarchy."
            ),
        },
    )


class MD024(Rule[MD024Config]):
    """Headings should have unique content."""

    id = "MD024"
    name = "no-duplicate-heading"
    summary = "Headings should have unique content"
    config_class = MD024Config

    description = (
        "This rule checks that heading content is unique throughout the document. "
        "When siblings_only is enabled, duplicate headings are only flagged if they "
        "appear within the same parent section."
    )

    rationale = (
        "Some Markdown parsers generate anchors for headings based on the heading "
        "text. Having multiple headings with the same content can cause problems "
        "with anchor links, making it impossible to navigate to specific sections."
    )

    example_valid = """\
# Heading 1

## Heading 2

### Heading 3

All headings have unique content.
"""

    example_invalid = """\
# Some text

## Some text

### Some text
"""

    @staticmethod
    def _get_heading_text(tokens: list, index: int) -> str:
        """Extract heading text from the inline token following a heading_open."""
        if index + 1 < len(tokens) and tokens[index + 1].type == "inline":
            return tokens[index + 1].content
        return ""

    def check(self, document: Document, config: MD024Config) -> list[Violation]:
        """Check for duplicate heading content."""
        if config.siblings_only:
            return self._check_siblings_only(document)
        return self._check_all_headings(document)

    def _check_all_headings(self, document: Document) -> list[Violation]:
        """Check for duplicate headings across the entire document."""
        violations: list[Violation] = []
        seen_headings: dict[str, int] = {}  # heading text -> first line number

        for i, token in enumerate(document.tokens):
            if token.type == "heading_open":
                line = token.map[0] + 1 if token.map else 1
                heading_text = self._get_heading_text(document.tokens, i)

                if heading_text in seen_headings:
                    context = document.get_line(line)
                    violations.append(
                        Violation(
                            line=line,
                            column=1,
                            rule_id=self.id,
                            rule_name=self.name,
                            message=f'Duplicate heading "{heading_text}"',
                            context=context,
                        )
                    )
                else:
                    seen_headings[heading_text] = line

        return violations

    def _check_siblings_only(self, document: Document) -> list[Violation]:
        """Check for duplicate headings only among siblings."""
        violations: list[Violation] = []

        # Track headings at each level within each parent context
        # Index 0 unused (levels are 1-6), each level has a set of seen headings
        level_headings: list[set[str]] = [set() for _ in range(7)]
        current_level = 0

        for i, token in enumerate(document.tokens):
            if token.type == "heading_open":
                level = int(token.tag[1])
                line = token.map[0] + 1 if token.map else 1
                heading_text = self._get_heading_text(document.tokens, i)

                # When moving to a shallower level, clear only deeper levels.
                # The target level retains its tracked headings since those are
                # siblings under the same parent.
                if level < current_level:
                    for j in range(level + 1, 7):
                        level_headings[j].clear()
                # When moving to a deeper level, initialize it as empty
                elif level > current_level:
                    level_headings[level].clear()

                # Check for duplicate at this level
                if heading_text in level_headings[level]:
                    context = document.get_line(line)
                    violations.append(
                        Violation(
                            line=line,
                            column=1,
                            rule_id=self.id,
                            rule_name=self.name,
                            message=f'Duplicate heading "{heading_text}"',
                            context=context,
                        )
                    )
                else:
                    level_headings[level].add(heading_text)

                current_level = level

        return violations
