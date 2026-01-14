import re
from dataclasses import dataclass, field

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD053Config(RuleConfig):
    """Configuration for MD053 rule."""

    ignored_definitions: list[str] = field(
        default_factory=lambda: ["//"],
        metadata={
            "description": "List of definition labels to ignore.",
        },
    )


class MD053(Rule[MD053Config]):
    """Link and image reference definitions should be needed."""

    id = "MD053"
    name = "link-image-reference-definitions"
    summary = "Link and image reference definitions should be needed"
    config_class = MD053Config

    description = (
        "This rule checks for link and image reference definitions that are "
        "either unused (not referenced by any link or image) or duplicated "
        "(the same label defined multiple times)."
    )

    rationale = (
        "Unused reference definitions clutter the document and may indicate "
        "incomplete editing. Duplicate definitions are confusing because only "
        "the first one is used by Markdown parsers. Removing unnecessary "
        "definitions keeps the document clean and maintainable."
    )

    example_valid = """\
# Valid Reference Links

All reference definitions below are used.

This is a [full reference link][example].

This is a [collapsed reference][].

This is a [shortcut reference].

An image: ![alt text][image]

[example]: https://example.com
[collapsed reference]: https://collapsed.example.com
[shortcut reference]: https://shortcut.example.com
[image]: https://example.com/image.png

[//]: # (This is an ignored comment-style definition)
"""

    example_invalid = """\
# Invalid Reference Links

This document has unused and duplicate reference definitions.

Here is a [used link][example].

[example]: https://example.com
[unused]: https://unused.example.com
[example]: https://duplicate.example.com
"""

    # Pattern to match reference definitions: [label]: url
    REFERENCE_DEF_PATTERN = re.compile(r"^ {0,3}\[([^\]]+)\]:\s*")

    # Patterns that extract reference labels from different link/image syntaxes.
    # Each pattern's group(1) captures the label that references a definition.
    REFERENCE_USE_PATTERNS = [
        re.compile(r"\[[^\]]*\]\[([^\]]+)\]"),  # Full: [text][ref]
        re.compile(r"\[([^\]]+)\]\[\]"),  # Collapsed: [text][]
        re.compile(r"(?<!!)\[([^\]]+)\](?!\[|\()"),  # Shortcut: [text]
        re.compile(r"!\[[^\]]*\]\[([^\]]+)\]"),  # Image full: ![alt][ref]
        re.compile(r"!\[([^\]]+)\]\[\]"),  # Image collapsed: ![alt][]
        re.compile(r"!\[([^\]]+)\](?!\[|\()"),  # Image shortcut: ![alt]
    ]

    def check(self, document: Document, config: MD053Config) -> list[Violation]:
        """Check for unused or duplicate link/image reference definitions."""
        violations: list[Violation] = []

        # Get lines that are inside code blocks or HTML blocks
        excluded_lines = self._get_code_block_lines(document)
        for token in document.tokens:
            if token.type == "html_block" and token.map:
                for line_num in range(token.map[0] + 1, token.map[1] + 1):
                    excluded_lines.add(line_num)

        # Get inline code span positions per line
        code_span_positions = self._get_code_span_positions(document)

        # Build set of ignored labels (lowercase for case-insensitive matching)
        ignored = {label.lower() for label in config.ignored_definitions}

        # Parse all reference definitions
        definitions: dict[str, list[int]] = {}  # label -> list of line numbers
        for line_num, line in enumerate(document.lines, start=1):
            if line_num in excluded_lines:
                continue

            match = self.REFERENCE_DEF_PATTERN.match(line)
            if match:
                label = match.group(1).lower()
                if label not in definitions:
                    definitions[label] = []
                definitions[label].append(line_num)

        # Collect all referenced labels
        references: set[str] = set()
        for line_num, line in enumerate(document.lines, start=1):
            if line_num in excluded_lines:
                continue

            # Skip reference definition lines for reference collection
            if self.REFERENCE_DEF_PATTERN.match(line):
                continue

            line_code_cols = code_span_positions.get(line_num, set())

            for pattern in self.REFERENCE_USE_PATTERNS:
                for match in pattern.finditer(line):
                    if match.start() + 1 not in line_code_cols:
                        references.add(match.group(1).lower())

        # Check for unused definitions
        for label, line_nums in definitions.items():
            if label in ignored:
                continue

            if label not in references:
                # First definition is unused
                line_num = line_nums[0]
                violations.append(
                    Violation(
                        line=line_num,
                        column=1,
                        rule_id=self.id,
                        rule_name=self.name,
                        message=f'Unused link or image reference definition: "{label}"',
                        context=document.get_line(line_num),
                    )
                )

            # Check for duplicate definitions (after the first)
            for dup_line_num in line_nums[1:]:
                violations.append(
                    Violation(
                        line=dup_line_num,
                        column=1,
                        rule_id=self.id,
                        rule_name=self.name,
                        message=f'Duplicate link or image reference definition: "{label}"',
                        context=document.get_line(dup_line_num),
                    )
                )

        return violations
