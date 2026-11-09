import re
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
    preserves_rendering = True

    SETEXT_UNDERLINE_RE = re.compile(r"-+[ \t]*")

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

    @staticmethod
    def _hr_style(document: Document, line: int) -> str:
        """Return the rule's text alone, since a quote marker or list bullet is not its style."""
        raw_line = document.get_line(line) or ""
        return raw_line[len(document.container_prefix(line)) :].strip()

    def _get_expected_style(self, document: Document, config: MD035Config) -> str | None:
        """Determine the expected HR style from config or the first HR in the document."""
        if config.style != "consistent":
            return config.style
        for token in document.tokens:
            if token.type == "hr":
                line = token.map[0] + 1 if token.map else 1
                return self._hr_style(document, line)
        return None

    def check(self, document: Document, config: MD035Config) -> list[Violation]:
        """Check for horizontal rule style consistency."""
        violations: list[Violation] = []

        expected_style = self._get_expected_style(document, config)

        for token in document.tokens:
            if token.type == "hr":
                line = token.map[0] + 1 if token.map else 1
                raw_line = document.get_line(line)
                current_style = self._hr_style(document, line)

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
        """Fix horizontal rules to use a consistent style.

        A rule is left unchanged when the new style would change what the line means: a
        dash rule under paragraph text becomes a setext heading underline, one on the first
        line can open front matter, and one after a bullet of the same character turns the
        list item into a single rule.
        """
        violations = self.check(document, config)
        if not violations:
            return None

        expected_style = self._get_expected_style(document, config)
        if expected_style is None:
            return None

        paragraph_ends = {
            token.map[1]
            for token in document.tokens
            if token.type == "paragraph_open" and token.map
        }
        setext_underline = self.SETEXT_UNDERLINE_RE.fullmatch(expected_style) is not None
        style_char = expected_style.strip()[:1]

        violation_lines = {v.line for v in violations}
        lines = document.content.split("\n")
        changed = False
        for line_num in violation_lines:
            raw_line = lines[line_num - 1]
            prefix = document.container_prefix(line_num)
            # Preserve leading whitespace
            content = raw_line[len(prefix) :]
            stripped = content.lstrip()
            leading = content[: len(content) - len(stripped)]
            fixed = prefix + leading + expected_style

            if setext_underline and line_num - 1 in paragraph_ends:
                continue
            if line_num == 1 and fixed.startswith("---"):
                continue
            if style_char and style_char in prefix:
                continue

            lines[line_num - 1] = fixed
            changed = True

        if not changed:
            return None

        return "\n".join(lines)
