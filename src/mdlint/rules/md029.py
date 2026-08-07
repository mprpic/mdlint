import re
from dataclasses import dataclass, field
from typing import Literal, NamedTuple

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


class _ListItem(NamedTuple):
    """An ordered list item prefix as written in the source."""

    number: int
    line: int
    digits: str
    content_column: int


@dataclass
class MD029Config(RuleConfig):
    """Configuration for MD029 rule."""

    OlPrefix = Literal["one", "ordered", "one_or_ordered", "zero"]

    style: OlPrefix = field(
        default="one_or_ordered",
        metadata={
            "description": "Required ordered list prefix style.",
            "option_descriptions": {
                "one": "All list items must use '1.' as the prefix",
                "ordered": (
                    "List items must use sequential numbering starting "
                    "from 0 or 1 (e.g. 1, 2, 3 or 0, 1, 2)"
                ),
                "one_or_ordered": ("Either 'one' or 'ordered' style is acceptable (auto-detected)"),
                "zero": "All list items must use '0.' as the prefix",
            },
        },
    )


class MD029(Rule[MD029Config]):
    """Ordered list item prefix should be consistent."""

    id = "MD029"
    name = "ol-prefix"
    summary = "Ordered list item prefix should be consistent"
    config_class = MD029Config

    description = (
        "This rule ensures that ordered list item prefixes follow a consistent "
        "pattern. The `style` setting controls which numbering pattern is enforced: "
        "`one` requires all items use '1.', `ordered` requires sequential numbering "
        "starting from 0 or 1, `zero` requires all items use '0.', and "
        "`one_or_ordered` (default) accepts either the 'one' or 'ordered' patterns, "
        "auto-detecting which is in use from the first two items.\n\n"
        "Prefixes may be zero-padded or space-padded so that list item "
        "content lines up (for example `08.`/`09.`/`10.` or ` 8.`/` 9.`/`10.`). "
        "Fixes preserve that alignment."
    )

    # An ordered list item prefix: indent, digits, marker, and trailing space
    PREFIX_PATTERN = re.compile(r"\s*(?P<digits>\d+)[.)](?:\s+|$)")

    rationale = (
        "Consistent formatting makes it easier to understand a document. "
        "Using '1.' for all items simplifies reordering since items can be "
        "moved without renumbering, while sequential numbering provides "
        "explicit ordering at a glance."
    )

    example_valid = """\
# Ordered List with Consistent Prefixes

1. First item
1. Second item
1. Third item
"""

    example_invalid = """\
# Ordered List with Inconsistent Prefixes

1. First item
3. Second item
2. Third item
"""

    def check(self, document: Document, config: MD029Config) -> list[Violation]:
        """Check for ordered list prefix violations."""
        violations: list[Violation] = []
        style = config.style

        # Track list contexts: each list gets its own numbering check
        list_stack: list[dict] = []

        for token in document.tokens:
            if token.type == "ordered_list_open":
                list_stack.append({"items": [], "ordered_start": 1})
            elif token.type == "ordered_list_close":
                if list_stack:
                    ctx = list_stack.pop()
                    if style == "one_or_ordered":
                        violations.extend(self._check_one_or_ordered(ctx["items"]))
            elif token.type == "list_item_open" and list_stack:
                line = token.map[0] + 1 if token.map else 1
                line_content = document.get_line(line)
                actual_prefix = self._extract_prefix(line_content)

                if actual_prefix is not None:
                    ctx = list_stack[-1]
                    ctx["items"].append((actual_prefix, line, line_content))
                    item_index = len(ctx["items"])

                    if style != "one_or_ordered":
                        expected = self._get_expected(style, ctx, item_index, actual_prefix)
                        if expected is not None and actual_prefix != expected:
                            violations.append(
                                Violation(
                                    line=line,
                                    column=1,
                                    rule_id=self.id,
                                    rule_name=self.name,
                                    message=(
                                        f"Ordered list item prefix: "
                                        f"expected {expected}, found {actual_prefix}"
                                    ),
                                    context=line_content,
                                ),
                            )

        return violations

    def _check_one_or_ordered(self, items: list[tuple[int, int, str]]) -> list[Violation]:
        """Check items using one_or_ordered auto-detection (matching JS logic).

        Examines the first two items to determine whether the list uses "one"
        (1/1/1) or "ordered" (1/2/3 or 0/1/2) style, then validates all items.
        """
        violations: list[Violation] = []
        if not items:
            return violations

        # Determine style based on first two items
        incrementing = False
        if len(items) >= 2:
            first_value = items[0][0]
            second_value = items[1][0]
            incrementing = (second_value != 1) or (first_value == 0)

        if incrementing:
            start = 0 if items[0][0] == 0 else 1
            for i, (prefix, line, line_content) in enumerate(items):
                expected = start + i
                if prefix != expected:
                    violations.append(
                        Violation(
                            line=line,
                            column=1,
                            rule_id=self.id,
                            rule_name=self.name,
                            message=(
                                f"Ordered list item prefix: expected {expected}, found {prefix}"
                            ),
                            context=line_content,
                        ),
                    )
        else:
            for prefix, line, line_content in items:
                if prefix != 1:
                    violations.append(
                        Violation(
                            line=line,
                            column=1,
                            rule_id=self.id,
                            rule_name=self.name,
                            message=(f"Ordered list item prefix: expected 1, found {prefix}"),
                            context=line_content,
                        ),
                    )

        return violations

    def fix(self, document: Document, config: MD029Config) -> str | None:
        """Fix ordered list item prefixes to match the configured style."""
        style = config.style

        # Collect list info using the same token traversal as check()
        lists: list[list[_ListItem]] = []
        list_stack: list[list[_ListItem]] = []

        for token in document.tokens:
            if token.type == "ordered_list_open":
                list_stack.append([])
            elif token.type == "ordered_list_close":
                if list_stack:
                    lists.append(list_stack.pop())
            elif token.type == "list_item_open" and list_stack:
                line = token.map[0] + 1 if token.map else 1
                item = self._parse_item(document.get_line(line), line)
                if item is not None:
                    list_stack[-1].append(item)

        replacements: dict[int, str] = {}  # line -> replacement digits

        for items in lists:
            if not items:
                continue

            expected_numbers: list[int] = []

            if style == "one":
                expected_numbers = [1] * len(items)
            elif style == "zero":
                expected_numbers = [0] * len(items)
            elif style == "ordered":
                start = 0 if items[0].number == 0 else 1
                expected_numbers = [start + i for i in range(len(items))]
            elif style == "one_or_ordered":
                # Auto-detect style from first two items
                incrementing = False
                if len(items) >= 2:
                    incrementing = (items[1].number != 1) or (items[0].number == 0)

                if incrementing:
                    start = 0 if items[0].number == 0 else 1
                    expected_numbers = [start + i for i in range(len(items))]
                else:
                    expected_numbers = [1] * len(items)

            padding = self._alignment_padding(items)
            for item, expected in zip(items, expected_numbers):
                if item.number != expected:
                    replacements[item.line] = self._render_digits(item, expected, padding)

        if not replacements:
            return None

        lines = document.content.split("\n")
        for line_num, new_digits in replacements.items():
            line_idx = line_num - 1
            line = lines[line_idx]
            stripped = line.lstrip()
            indent = line[: len(line) - len(stripped)]
            # Replace the numeric prefix (digits followed by . or ))
            i = 0
            while i < len(stripped) and stripped[i].isdigit():
                i += 1
            if i > 0 and i < len(stripped) and stripped[i] in ".)":
                lines[line_idx] = indent + new_digits + stripped[i:]

        return "\n".join(lines)

    @classmethod
    def _extract_prefix(cls, line: str | None) -> int | None:
        """Extract the numeric prefix from an ordered list item line."""
        if line is None:
            return None
        match = cls.PREFIX_PATTERN.match(line)
        return int(match.group("digits")) if match else None

    @classmethod
    def _parse_item(cls, line_content: str | None, line: int) -> _ListItem | None:
        """Parse an ordered list item line into its prefix components."""
        if line_content is None:
            return None
        match = cls.PREFIX_PATTERN.match(line_content)
        if match is None:
            return None
        digits = match.group("digits")
        return _ListItem(int(digits), line, digits, match.end() + 1)

    @staticmethod
    def _alignment_padding(items: list[_ListItem]) -> str | None:
        """Get the character to pad renumbered prefixes with, or None for no padding.

        A list whose items all start their content at the same column is being
        kept aligned deliberately, either by zero-padding (`08.`) or by
        space-padding (` 8.`). Renumbering such a list has to keep the prefixes
        the same width, or the alignment is lost.

        Args:
            items: The items of a single ordered list.

        Returns:
            "0" or " " if the list is aligned, None otherwise.
        """
        if len({item.content_column for item in items}) != 1:
            return None
        return "0" if items[0].digits.startswith("0") else " "

    @staticmethod
    def _render_digits(item: _ListItem, expected: int, padding: str | None) -> str:
        """Render a replacement prefix, padded to the width of the original."""
        digits = str(expected)
        return digits if padding is None else digits.rjust(len(item.digits), padding)

    @staticmethod
    def _get_expected(
        style: str,
        ctx: dict,
        item_index: int,
        actual_prefix: int,
    ) -> int | None:
        """Determine the expected prefix value for one/zero/ordered styles."""
        if style == "one":
            return 1
        elif style == "zero":
            return 0
        elif style == "ordered":
            if item_index == 1:
                if actual_prefix == 0:
                    ctx["ordered_start"] = 0
                    return 0
                else:
                    ctx["ordered_start"] = 1
                    return 1
            else:
                return ctx["ordered_start"] + item_index - 1
        return None
