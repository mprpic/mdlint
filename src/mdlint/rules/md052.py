import re
from dataclasses import dataclass, field

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD052Config(RuleConfig):
    """Configuration for MD052 rule."""

    shortcut_syntax: bool = field(
        default=False,
        metadata={
            "description": "Whether to check shortcut syntax (e.g., `[label]`).",
        },
    )
    ignored_labels: list[str] = field(
        default_factory=lambda: ["x"],
        metadata={
            "description": "List of labels to ignore (e.g., `x` for task lists).",
        },
    )


class MD052(Rule[MD052Config]):
    """Reference links and images should use a label that is defined."""

    id = "MD052"
    name = "reference-links-images"
    summary = "Reference links and images should use a label that is defined"
    config_class = MD052Config

    description = (
        "This rule checks that all reference-style links and images use labels "
        "that are actually defined in the document. Reference links use the format "
        "`[text][label]` (full) or `[label][]` (collapsed), and must have a corresponding "
        "`[label]: URL` definition. Shortcut syntax (`[label]`) is not checked by default "
        "because it is ambiguous — the text `[example]` could be a shortcut link or simply "
        'the word "example" in brackets. To include shortcut syntax, set the '
        "`shortcut_syntax` option to `true`. Brackets can be escaped with `\\` to avoid "
        "false positives: `\\[example\\]`."
    )

    rationale = (
        "When a reference link or image uses a label that is not defined, the link "
        "will not render correctly and will display as literal text with brackets. "
    )

    example_valid = """\
# Document with Defined References

This is a [full reference][label] link.

This is a [collapsed][] link.

This is an image: ![alt text][image]

[label]: https://example.com/label
[collapsed]: https://example.com/collapsed
[image]: https://example.com/image.png
"""

    example_invalid = """\
# Document with Undefined References

This is a [full reference][undefined] link.

This is a [missing][] collapsed link.

This is an image: ![alt text][no-image]
"""

    # Pattern for full reference links/images: [text][label] or ![alt][label]
    FULL_REF_PATTERN = re.compile(r"!?\[[^\]]*\]\[([^\]]+)\]")

    # Pattern for collapsed reference links/images: [label][] or ![label][]
    COLLAPSED_REF_PATTERN = re.compile(r"!?\[([^\]]+)\]\[\]")

    # Pattern for shortcut reference links/images: [label] or ![label]
    # Must not be followed by (, [, or : to avoid matching inline links and definitions
    SHORTCUT_REF_PATTERN = re.compile(r"!?\[([^\]]+)\](?!\[|\(|:)")

    def check(self, document: Document, config: MD052Config) -> list[Violation]:
        """Check for undefined reference link/image violations."""
        violations: list[Violation] = []

        # Build set of defined labels (case-insensitive)
        defined_labels = set(self._get_reference_definitions(document).keys())

        # Build set of ignored labels (case-insensitive)
        ignored = {label.lower() for label in config.ignored_labels}

        # Get lines in code blocks and HTML blocks to skip
        skip_lines = self._get_code_block_lines(document) | self._get_html_block_lines(document)

        # Get inline code span columns per line
        code_span_positions = self._get_code_span_positions(document)

        # Patterns to check: (pattern, extra_filter)
        patterns: list[tuple[re.Pattern, bool]] = [
            (self.FULL_REF_PATTERN, False),
            (self.COLLAPSED_REF_PATTERN, False),
        ]
        if config.shortcut_syntax:
            patterns.append((self.SHORTCUT_REF_PATTERN, True))

        # Check each line for undefined references
        for line_num, line in enumerate(document.lines, start=1):
            if line_num in skip_lines:
                continue

            for pattern, check_collapsed in patterns:
                for match in pattern.finditer(line):
                    column = match.start() + 1

                    if column in code_span_positions.get(line_num, set()):
                        continue

                    # For shortcut refs, skip if already matched as collapsed reference
                    if check_collapsed and self._is_collapsed_reference(line, match.start()):
                        continue

                    label = match.group(1).lower()
                    if label not in defined_labels and label not in ignored:
                        label_name = match.group(1)
                        violations.append(
                            Violation(
                                line=line_num,
                                column=column,
                                rule_id=self.id,
                                rule_name=self.name,
                                message=f'Missing link/image reference definition: "{label_name}"',
                                context=document.get_line(line_num),
                            )
                        )

        return violations

    @staticmethod
    def _is_collapsed_reference(line: str, position: int) -> bool:
        """Check if position is part of a collapsed reference (has trailing []).

        Args:
            line: The line content.
            position: Position of the opening bracket.

        Returns:
            True if this is a collapsed reference.
        """
        # Find the closing bracket of the first part
        bracket_count = 0
        i = position
        while i < len(line):
            if line[i] == "[":
                bracket_count += 1
            elif line[i] == "]":
                bracket_count -= 1
                if bracket_count == 0:
                    # Check if followed by []
                    if i + 2 < len(line) and line[i + 1 : i + 3] == "[]":
                        return True
                    break
            i += 1
        return False
