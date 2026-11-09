from dataclasses import dataclass, field
from typing import Literal, NamedTuple

from markdown_it.token import Token

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.rules.md030 import find_list_marker
from mdlint.violation import Violation


class _ListItem(NamedTuple):
    """An ordered list item prefix as written in the source."""

    number: int
    line: int
    digits: str
    start: int  # offset of the digits in the line
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
    preserves_rendering = True

    description = (
        "This rule ensures that ordered list item prefixes follow a consistent "
        "pattern. The `style` setting controls which numbering pattern is enforced: "
        "`one` requires all items use '1.', `ordered` requires sequential numbering "
        "starting from 0 or 1, `zero` requires all items use '0.', and "
        "`one_or_ordered` (default) accepts either the 'one' or 'ordered' patterns, "
        "auto-detecting which is in use from the first two items.\n\n"
        "A list may start at another number, for example to continue an earlier list "
        "after a paragraph. Its first item is still reported, but the fix leaves it "
        "alone because it sets the number the rendered list starts at, and the items "
        "after it are expected to count up from it.\n\n"
        "Prefixes may be zero-padded or space-padded so that list item "
        "content lines up (for example `08.`/`09.`/`10.` or ` 8.`/` 9.`/`10.`). "
        "Fixes preserve that alignment."
    )

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
        list_stack: list[list[tuple[int, int, str | None]]] = []
        open_items: list[int] = []  # first lines of the enclosing list items

        for token in document.tokens:
            if token.type == "ordered_list_open":
                list_stack.append([])
            elif token.type == "ordered_list_close":
                if list_stack:
                    violations.extend(self._check_list(list_stack.pop(), style))
            elif token.type == "list_item_close":
                open_items.pop()
            elif token.type == "list_item_open" and token.map:
                line = token.map[0] + 1
                item = self._parse_item(document, token, line, open_items.count(line))
                open_items.append(line)
                if item is not None and list_stack:
                    list_stack[-1].append((item.number, line, document.get_line(line)))

        return sorted(violations, key=lambda v: v.line)

    @staticmethod
    def _expected_numbers(style: str, numbers: list[int]) -> list[int]:
        """Expected prefix of each item of one list.

        The first item must use the style's starting number, but later items count up from
        the number it actually has: only that number changes the rendered list (it becomes
        the list's start), so a list that deliberately starts at 3 is reported once and the
        fix can leave its start alone.
        """
        first = numbers[0]
        if style == "one_or_ordered":
            # Auto-detect the style from the first two items, like markdownlint
            incrementing = len(numbers) >= 2 and (numbers[1] != 1 or first == 0)
            style = "ordered" if incrementing else "one"
        if style == "one":
            return [1] * len(numbers)
        if style == "zero":
            return [0] * len(numbers)
        return [0 if first == 0 else 1] + [first + i for i in range(1, len(numbers))]

    def _check_list(self, items: list[tuple[int, int, str | None]], style: str) -> list[Violation]:
        """Report the items of one list whose prefix differs from the expected one."""
        if not items:
            return []
        expected_numbers = self._expected_numbers(style, [number for number, _, _ in items])
        return [
            Violation(
                line=line,
                column=1,
                rule_id=self.id,
                rule_name=self.name,
                message=f"Ordered list item prefix: expected {expected}, found {number}",
                context=line_content,
            )
            for (number, line, line_content), expected in zip(items, expected_numbers)
            if number != expected
        ]

    def fix(self, document: Document, config: MD029Config) -> str | None:
        """Fix ordered list item prefixes to match the configured style."""
        style = config.style

        # Collect list info using the same token traversal as check()
        lists: list[list[_ListItem]] = []
        list_stack: list[list[_ListItem]] = []
        open_items: list[int] = []  # first lines of the enclosing list items

        for token in document.tokens:
            if token.type == "ordered_list_open":
                list_stack.append([])
            elif token.type == "ordered_list_close":
                if list_stack:
                    lists.append(list_stack.pop())
            elif token.type == "list_item_close":
                open_items.pop()
            elif token.type == "list_item_open" and token.map:
                line = token.map[0] + 1
                item = self._parse_item(document, token, line, open_items.count(line))
                open_items.append(line)
                if item is not None and list_stack:
                    list_stack[-1].append(item)

        replacements: list[tuple[_ListItem, str]] = []

        for items in lists:
            if not items:
                continue

            expected_numbers = self._expected_numbers(style, [item.number for item in items])
            padding = self._alignment_padding(items)
            # The first number sets where the rendered list starts, so it is never changed.
            for item, expected in zip(items[1:], expected_numbers[1:]):
                if item.number != expected:
                    replacements.append((item, self._render_digits(item, expected, padding)))

        if not replacements:
            return None

        lines = document.content.split("\n")
        # Right to left, so a renumbered parent cannot move a child's digits on the same line.
        for item, new_digits in sorted(
            replacements, key=lambda r: (r[0].line, r[0].start), reverse=True
        ):
            line = lines[item.line - 1]
            end = item.start + len(item.digits)
            lines[item.line - 1] = line[: item.start] + new_digits + line[end:]

        return "\n".join(lines)

    @staticmethod
    def _parse_item(
        document: Document, token: Token, line: int, outer_items: int
    ) -> _ListItem | None:
        """Parse an ordered list item's prefix as written in the source.

        Args:
            document: The document being checked.
            token: A ``list_item_open`` token.
            line: The item's first line.
            outer_items: How many enclosing list items open on the same line.

        Returns:
            The item's prefix, or None for bullet items and items whose marker is not found.
        """
        line_content = document.get_line(line)
        if token.markup not in (".", ")") or line_content is None:
            return None
        match = find_list_marker(line_content, token, outer_items)
        if match is None:
            return None
        return _ListItem(int(token.info), line, token.info, match.start("marker"), match.end() + 1)

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
