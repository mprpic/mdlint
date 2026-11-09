import re
from dataclasses import dataclass, field

from mdlint.document import (
    Document,
    ReferenceDefinition,
    is_blank_line,
    normalize_reference_label,
)
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
    preserves_rendering = True

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

    def _parse_definitions_and_references(
        self, document: Document, config: MD053Config
    ) -> tuple[dict[str, list[ReferenceDefinition]], set[str]]:
        """Parse reference definitions and collect referenced labels.

        Returns (definitions, references) where definitions maps normalized labels
        to their definitions in source order, and references is a set of normalized
        labels used.
        """
        excluded_lines = (
            document.code_block_lines
            | document.html_block_lines
            | document.reference_definition_lines
        )
        code_span_positions = document.code_span_positions
        ignored = {normalize_reference_label(label) for label in config.ignored_definitions}

        definitions: dict[str, list[ReferenceDefinition]] = {}
        for definition in document.reference_definition_entries:
            if definition.label not in ignored:
                definitions.setdefault(definition.label, []).append(definition)

        references: set[str] = set()
        for line_num, line in enumerate(document.lines, start=1):
            if line_num in excluded_lines:
                continue

            if "[" not in line:
                continue

            line_code_cols = code_span_positions.get(line_num, set())
            for pattern in self.REFERENCE_USE_PATTERNS:
                for ref_match in pattern.finditer(line):
                    if ref_match.start() + 1 not in line_code_cols:
                        references.add(normalize_reference_label(ref_match.group(1)))

        return definitions, references

    def _unused_labels(
        self, document: Document, config: MD053Config
    ) -> tuple[dict[str, list[ReferenceDefinition]], set[str]]:
        """Return the definitions by label and the labels no link or image uses.

        The line-by-line search finds most uses cheaply, but not references that wrap lines,
        hold brackets or escapes, or come from a malformed inline link that falls back to a
        reference. So each label it finds no use for is confirmed with the parser: the
        definition's label is renamed in a copy, and if the rendered page changes, something
        used it.
        """
        definitions, references = self._parse_definitions_and_references(document, config)
        rendered = Document.render_html(document.content)
        unused = {
            label
            for label, label_definitions in definitions.items()
            if label not in references
            and Document.render_html(self._rename_label(document, label_definitions[0])) == rendered
        }
        return definitions, unused

    @staticmethod
    def _rename_label(document: Document, definition: ReferenceDefinition) -> str:
        """Content with the definition's label changed, so no reference can resolve to it."""
        lines = document.content.split("\n")
        line = lines[definition.start_line - 1]
        bracket = line.index("[", len(document.container_prefix(definition.start_line)))
        lines[definition.start_line - 1] = (
            line[: bracket + 1] + "mdlint unused probe " + line[bracket + 1 :]
        )
        return "\n".join(lines)

    def check(self, document: Document, config: MD053Config) -> list[Violation]:
        """Check for unused or duplicate link/image reference definitions."""
        violations: list[Violation] = []
        definitions, unused = self._unused_labels(document, config)

        for label, label_definitions in definitions.items():
            line_nums = [definition.start_line for definition in label_definitions]
            if label in unused:
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

    def fix(self, document: Document, config: MD053Config) -> str | None:
        """Fix by removing unused and duplicate reference definitions.

        A definition that starts on a list item's marker line is left alone, because
        removing that line would remove the marker and detach the rest of the item. Each
        removal is kept only if the rendered page stays the same, so a definition that
        separates two lists or code blocks (which would merge without it) is kept.
        """
        definitions, unused = self._unused_labels(document, config)
        rendered = Document.render_html(document.content)

        lines_to_remove: set[int] = set()
        for label, label_definitions in definitions.items():
            removable = label_definitions if label in unused else label_definitions[1:]
            for definition in removable:
                prefix = document.container_prefix(definition.start_line)
                if prefix.replace(">", "").strip():
                    continue
                trial = lines_to_remove | set(range(definition.start_line, definition.end_line + 1))
                if Document.render_html(self._remove_lines(document, trial)) == rendered:
                    lines_to_remove = trial

        if not lines_to_remove:
            return None
        return self._remove_lines(document, lines_to_remove)

    @staticmethod
    def _remove_lines(document: Document, lines_to_remove: set[int]) -> str:
        """Content without the given 1-indexed lines.

        Consecutive blank lines are collapsed only where the removal created them.
        """
        lines = document.content.split("\n")
        result: list[str] = []
        prev_blank = False
        just_removed = False
        for line_num, line in enumerate(lines, start=1):
            if line_num in lines_to_remove:
                just_removed = True
                continue
            # A comment separates blocks like a blank line does, but it is content to keep.
            is_blank = is_blank_line(line) and "<!--" not in line
            if is_blank and prev_blank and just_removed:
                # Keep the shallower of the two blank lines so a quote does not end on ">".
                if line.count(">") < result[-1].count(">"):
                    result[-1] = line
                continue
            result.append(line)
            prev_blank = is_blank
            just_removed = False

        return "\n".join(result)
