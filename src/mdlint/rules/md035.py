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

    def _get_expected_style(self, document: Document, config: MD035Config) -> str | None:
        """Determine the expected HR style from config or the first HR in the document."""
        if config.style != "consistent":
            return config.style
        for token in document.tokens:
            if token.type == "hr":
                line = token.map[0] + 1 if token.map else 1
                raw_line = document.get_line(line)
                return raw_line.strip() if raw_line else ""
        return None

    def check(self, document: Document, config: MD035Config) -> list[Violation]:
        """Check for horizontal rule style consistency."""
        violations: list[Violation] = []

        expected_style = self._get_expected_style(document, config)

        for token in document.tokens:
            if token.type == "hr":
                line = token.map[0] + 1 if token.map else 1
                raw_line = document.get_line(line)
                current_style = raw_line.strip() if raw_line else ""

                # For consistent mode, skip the first HR (it sets the style)
                if current_style == expected_style:
                    continue

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

    def fix(self, document: Document, config: MD035Config) -> str | None:
        """Fix horizontal rules to use a consistent style."""
        violations = self.check(document, config)
        if not violations:
            return None

        expected_style = self._get_expected_style(document, config)
        if expected_style is None:
            return None

        violation_lines = {v.line for v in violations}
        lines = document.content.split("\n")
        for line_num in violation_lines:
            raw_line = lines[line_num - 1]
            # Preserve leading whitespace
            stripped = raw_line.lstrip()
            leading = raw_line[: len(raw_line) - len(stripped)]
            lines[line_num - 1] = leading + expected_style

        return "\n".join(lines)
