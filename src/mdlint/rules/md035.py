from dataclasses import dataclass, field

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD035Config(RuleConfig):
    """Configuration for MD035 rule."""

    style: str = field(
        default="consistent",
        metadata={
            "description": (
                "Required horizontal rule style. Use `consistent` to enforce that "
                "all horizontal rules match the first one, or specify an exact "
                "style like `---`, `***`, `- - -`, etc."
            ),
        },
    )


class MD035(Rule[MD035Config]):
    """Horizontal rule style should be consistent."""

    id = "MD035"
    name = "hr-style"
    summary = "Horizontal rule style should be consistent"
    config_class = MD035Config

    description = (
        "This rule enforces consistent horizontal rule styles throughout a document. "
        "It triggers when different horizontal rule formats are used, such as "
        "mixing `---` with `***`. Rules with different lengths "
        "(e.g., `---` vs `----`) or different characters (e.g., `---` vs `___`) "
        "are also considered different styles."
    )

    rationale = (
        "Consistent formatting makes it easier to understand a document. "
        "Using the same horizontal rule style throughout improves maintainability."
    )

    example_valid = """\
# Document with consistent horizontal rules

Some text here.

---

More text here.

---

Final section.
"""

    example_invalid = """\
# Document with inconsistent horizontal rules

Some text here.

---

More text here.

***

Final section.
"""

    def check(self, document: Document, config: MD035Config) -> list[Violation]:
        """Check for horizontal rule style consistency."""
        violations: list[Violation] = []

        style = config.style
        expected_style: str | None = None if style == "consistent" else style

        for token in document.tokens:
            if token.type == "hr":
                line = token.map[0] + 1 if token.map else 1
                # Get actual horizontal rule text from the raw line
                raw_line = document.get_line(line)
                current_style = raw_line.strip() if raw_line else ""

                # For consistent mode, set expected from first horizontal rule
                if expected_style is None:
                    expected_style = current_style
                    continue

                if current_style != expected_style:
                    violations.append(
                        Violation(
                            line=line,
                            column=1,
                            rule_id=self.id,
                            rule_name=self.name,
                            message=f"Expected '{expected_style}', found '{current_style}'",
                            context=raw_line,
                        )
                    )

        return violations
