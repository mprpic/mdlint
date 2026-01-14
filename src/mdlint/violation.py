from dataclasses import dataclass


@dataclass(frozen=True)
class Violation:
    """Represents a single style violation detected in a Markdown file.

    Attributes:
        line: 1-indexed line number where violation starts.
        column: 1-indexed column number (1 if not applicable).
        rule_id: Rule identifier (e.g., "MD001").
        rule_name: Rule name/alias (e.g., "heading-increment").
        message: Human-readable description of the violation.
        context: Optional: the offending line content.
    """

    line: int
    column: int
    rule_id: str
    rule_name: str
    message: str
    context: str | None = None

    def __post_init__(self) -> None:
        """Validate violation fields."""
        if self.line < 1:
            raise ValueError(f"line must be >= 1, got {self.line}")
        if self.column < 1:
            raise ValueError(f"column must be >= 1, got {self.column}")
