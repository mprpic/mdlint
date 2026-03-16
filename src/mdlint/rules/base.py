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
