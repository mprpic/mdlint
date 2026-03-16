from dataclasses import dataclass, field

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD031Config(RuleConfig):
    """Configuration for MD031 rule."""

    list_items: bool = field(
        default=True,
        metadata={
            "description": "Whether to check code fences inside list items.",
        },
    )


class MD031(Rule[MD031Config]):
    """Fenced code blocks should be surrounded by blank lines."""

    id = "MD031"
    name = "blanks-around-fences"
    summary = "Fenced code blocks should be surrounded by blank lines"
    config_class = MD031Config

    description = (
        "This rule enforces blank lines around fenced code blocks. It triggers "
        "when code fences are not preceded or followed by blank lines. The first "
        "code fence in a document does not require a blank line above, and a code "
        "fence at the end of a document does not require a blank line below. "
        "Set ``list_items`` to ``false`` to disable this rule for code fences "
        "inside list items. This can be useful when creating tight lists "
        "containing code fences."
    )

    rationale = (
        "Some parsers require a blank line before fenced code blocks when "
        "they follow a paragraph, or the fence may be treated as literal text. "
        "Consistent spacing around code blocks also improves readability."
    )

    example_valid = """\
Some text here.

```python
def hello():
    print("Hello!")
```

Some more text here.
"""

    example_invalid = """\
Some text here.
```python
def hello():
    print("Hello!")
```
Some more text here.
"""

    def _get_fences(self, document: Document, config: MD031Config) -> list[tuple[int, int]]:
        """Return 0-indexed (start, end) ranges for applicable fence tokens."""
        if not config.list_items:
            list_ranges = [
                (token.map[0], token.map[1])
                for token in document.tokens
                if token.type in ("bullet_list_open", "ordered_list_open") and token.map
            ]
        else:
            list_ranges = []

        fences: list[tuple[int, int]] = []
        for token in document.tokens:
            if token.type == "fence" and token.map:
                if not config.list_items and any(
                    start <= token.map[0] < end for start, end in list_ranges
                ):
                    continue
                fences.append((token.map[0], token.map[1]))
        return fences

    def check(self, document: Document, config: MD031Config) -> list[Violation]:
        """Check for blanks-around-fences violations."""
        violations: list[Violation] = []

        for fence_start, fence_end in self._get_fences(document, config):
            fence_start_line = fence_start + 1  # 1-indexed
            fence_end_line = fence_end  # exclusive, so last line is map[1]

            # Check blank line above
            if fence_start_line > 1:
                line_above = document.get_line(fence_start_line - 1)
                if line_above is not None and line_above.strip() != "":
                    violations.append(
                        Violation(
                            line=fence_start_line,
                            column=1,
                            rule_id=self.id,
                            rule_name=self.name,
                            message="Fenced code block should be preceded by a blank line",
                            context=document.get_line(fence_start_line),
                        )
                    )

            # Check blank line below
            if fence_end_line < len(document.lines):
                line_below = document.get_line(fence_end_line + 1)
                if line_below is not None and line_below.strip() != "":
                    violations.append(
                        Violation(
                            line=fence_end_line,
                            column=1,
                            rule_id=self.id,
                            rule_name=self.name,
                            message="Fenced code block should be followed by a blank line",
                            context=document.get_line(fence_end_line),
                        )
                    )

        return violations

    def fix(self, document: Document, config: MD031Config) -> str | None:
        """Fix blanks-around-fences violations by inserting missing blank lines."""
        fences = self._get_fences(document, config)

        if not fences:
            return None

        lines = document.content.split("\n")
        num_doc_lines = len(document.lines)
        changed = False

        # Process fences from bottom to top so insertions don't shift indices
        for fence_start, fence_end in reversed(fences):
            # fence_start is 0-indexed line of opening fence
            # fence_end is 0-indexed exclusive end (first line after closing fence)

            # Fix blank line below
            if fence_end < num_doc_lines:
                if lines[fence_end].strip() != "":
                    lines.insert(fence_end, "")
                    changed = True

            # Fix blank line above
            if fence_start > 0:
                if lines[fence_start - 1].strip() != "":
                    lines.insert(fence_start, "")
                    changed = True

        if not changed:
            return None

        return "\n".join(lines)
