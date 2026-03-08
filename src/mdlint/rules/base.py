import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

from mdlint.document import Document
from mdlint.violation import Violation


@dataclass
class RuleConfig:
    """Base configuration for rules."""

    pass


ConfigT = TypeVar("ConfigT", bound=RuleConfig)


class Rule(ABC, Generic[ConfigT]):
    """Base class for all linting rules."""

    id: str  # e.g., "MD001"
    name: str  # e.g., "heading-increment"
    summary: str  # Short one-line description
    config_class: type[RuleConfig] = RuleConfig

    # Extended documentation
    description: str | None = None  # Detailed explanation of what the rule checks
    rationale: str | None = None  # Why this rule matters

    # Examples for documentation (should match tests/fixtures/<id>/valid.md and invalid.md)
    example_valid: str | None = None
    example_invalid: str | None = None

    # Pattern to match reference definitions: [ref]: destination
    REFERENCE_DEF_PATTERN = re.compile(r"^\s*\[([^\]]+)\]:\s*(.*)$")

    @property
    def fixable(self) -> bool:
        return type(self).fix is not Rule.fix

    @abstractmethod
    def check(self, document: Document, config: ConfigT) -> list[Violation]:
        """Check document for violations.

        Args:
            document: The parsed document to check.
            config: Rule-specific configuration.

        Returns:
            List of violations found.
        """

    def fix(self, document: Document, config: ConfigT) -> str | None:  # noqa: ARG002
        """Fix violations in the document. Override in fixable rules.

        Returns fixed content string, or None if nothing was fixed.
        """
        return None

    @staticmethod
    def _get_code_block_lines(document: Document) -> set[int]:
        """Get set of line numbers that are inside code blocks.

        Returns:
            Set of 1-indexed line numbers that are part of code blocks.
        """
        code_lines: set[int] = set()

        for token in document.tokens:
            if token.type in ("fence", "code_block") and token.map:
                start_line = token.map[0] + 1
                end_line = token.map[1]
                for line_num in range(start_line, end_line + 1):
                    code_lines.add(line_num)

        return code_lines

    @staticmethod
    def _get_html_block_lines(document: Document) -> set[int]:
        """Get set of line numbers that are inside HTML blocks.

        Returns:
            Set of 1-indexed line numbers that are part of HTML blocks.
        """
        html_lines: set[int] = set()

        for token in document.tokens:
            if token.type == "html_block" and token.map:
                for line_num in range(token.map[0] + 1, token.map[1] + 1):
                    html_lines.add(line_num)

        return html_lines

    @staticmethod
    def _overlaps_ranges(start: int, end: int, ranges: list[tuple[int, int]]) -> bool:
        """Check if a position range overlaps with any existing ranges.

        Args:
            start: Start position (0-indexed).
            end: End position (0-indexed, exclusive).
            ranges: List of (start, end) tuples.

        Returns:
            True if the range overlaps with any existing range.
        """
        for range_start, range_end in ranges:
            if start < range_end and end > range_start:
                return True
        return False

    @staticmethod
    def _get_code_span_positions(document: Document) -> dict[int, set[int]]:
        """Get column positions that are inside inline code spans.

        Walks the AST to find code_inline tokens, then locates their positions
        in the source lines using the token's markup and content.

        Returns:
            Dict mapping 1-indexed line numbers to sets of 1-indexed column
            positions that are inside inline code spans.
        """
        code_columns: dict[int, set[int]] = {}

        for token in document.tokens:
            if token.type != "inline" or not token.map or not token.children:
                continue

            for line_num in range(token.map[0] + 1, token.map[1] + 1):
                line = document.get_line(line_num)
                if not line:
                    continue

                search_start = 0
                for child in token.children:
                    if child.type != "code_inline":
                        continue
                    # Reconstruct the full source text: delimiter + content + delimiter
                    full_span = child.markup + child.content + child.markup
                    idx = line.find(full_span, search_start)
                    if idx >= 0:
                        cols = code_columns.setdefault(line_num, set())
                        for col in range(idx + 1, idx + len(full_span) + 1):
                            cols.add(col)
                        search_start = idx + len(full_span)

        return code_columns

    @classmethod
    def _get_reference_definitions(cls, document: Document) -> dict[str, str]:
        """Parse reference definitions from the document.

        Returns:
            Dict mapping lowercase reference IDs to their destinations.
        """
        definitions: dict[str, str] = {}

        for line in document.lines:
            match = cls.REFERENCE_DEF_PATTERN.match(line)
            if match:
                ref_id = match.group(1).lower()
                destination = match.group(2).strip()
                definitions[ref_id] = destination

        return definitions
