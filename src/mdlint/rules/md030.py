import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import NamedTuple

from markdown_it.token import Token

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation

# One piece of the container syntax in front of a list item's content: a blockquote marker,
# or a list marker with the whitespace after it.
_CONTAINER_MARKER = re.compile(r"[ \t]*(?:>|(?P<marker>\d{1,9}[.)]|[-+*])(?P<space>[ \t]+|$))")
_QUOTE_MARKER = re.compile(r"[ \t]*>")


def find_list_marker(line: str, token: Token, outer_items: int) -> re.Match[str] | None:
    """Locate a list item's marker on the item's first line.

    ``Document.container_prefix`` covers the item's own marker as well and stops early on
    tab-indented lines, so it cannot say where the marker is. Everything in front of the
    marker is container syntax, though: ``>`` markers, indentation, and the markers of
    enclosing items that open on the same line. Skipping ``outer_items`` list markers
    therefore lands on this item's marker, which is then confirmed against the token.

    Args:
        line: The item's first line.
        token: The item's ``list_item_open`` token.
        outer_items: How many enclosing list items open on the same line.

    Returns:
        A match with the marker in its ``marker`` group and the whitespace after it in its
        ``space`` group, or None if the marker is not where the token says it is.
    """
    pos = 0
    while match := _CONTAINER_MARKER.match(line, pos):
        if match.group("marker") is not None:
            if outer_items == 0:
                return match if match.group("marker") == token.info + token.markup else None
            outer_items -= 1
        pos = match.end()
    return None


@dataclass
class MD030Config(RuleConfig):
    """Configuration for MD030 rule."""

    ul_single: int = field(
        default=1,
        metadata={
            "description": "Spaces after unordered list markers for single-paragraph items.",
        },
    )
    ol_single: int = field(
        default=1,
        metadata={
            "description": "Spaces after ordered list markers for single-paragraph items.",
        },
    )
    ul_multi: int = field(
        default=1,
        metadata={
            "description": "Spaces after unordered list markers for multi-paragraph items.",
        },
    )
    ol_multi: int = field(
        default=1,
        metadata={
            "description": "Spaces after ordered list markers for multi-paragraph items.",
        },
    )


class _MarkerSpacing(NamedTuple):
    """A list item whose marker is followed by the wrong number of spaces."""

    token: Token
    line: int
    end_line: int  # last line of the item
    match: re.Match[str]
    expected: int
    outer_items: int  # enclosing list items that open on the item's first line
    quotes: int  # enclosing blockquotes


class MD030(Rule[MD030Config]):
    """Spaces after list markers."""

    id = "MD030"
    name = "list-marker-space"
    summary = "Spaces after list markers"
    config_class = MD030Config
    preserves_rendering = True

    description = (
        "This rule checks the number of spaces between list markers "
        "(such as `-`, `*`, `+`, `1.`, or `1)`) and the text of list items, "
        "including lists inside blockquotes. It supports "
        "different spacing requirements for single-paragraph and "
        "multi-paragraph list items."
    )

    rationale = (
        "Consistent spacing after list markers improves readability and "
        "ensures documents render correctly across different Markdown "
        "parsers. Some style guides require additional spaces for "
        "multi-paragraph list items to align continuation paragraphs."
    )

    example_valid = """\
# Valid List Marker Spacing

- Item one
- Item two
- Item three

1. First item
2. Second item
3. Third item
"""

    example_invalid = """\
# Invalid List Marker Spacing

-  Item with two spaces
-   Item with three spaces

1.  First item with two spaces
2.   Second item with three spaces
"""

    def _iter_violating_items(
        self, document: Document, config: MD030Config
    ) -> Iterator[_MarkerSpacing]:
        """Yield the list items whose marker spacing does not match the configuration."""
        list_stack: list[tuple[str, bool]] = []
        list_info: dict[int, bool] = {}
        self._analyze_lists(document.tokens, list_info)
        open_items: list[int] = []  # first lines of the enclosing list items
        quotes = 0

        for token_index, token in enumerate(document.tokens):
            if token.type == "bullet_list_open":
                is_multi = list_info.get(token_index, False)
                list_stack.append(("ul", is_multi))
            elif token.type == "ordered_list_open":
                is_multi = list_info.get(token_index, False)
                list_stack.append(("ol", is_multi))
            elif token.type in ("bullet_list_close", "ordered_list_close"):
                if list_stack:
                    list_stack.pop()
            elif token.type == "blockquote_open":
                quotes += 1
            elif token.type == "blockquote_close":
                quotes -= 1
            elif token.type == "list_item_close":
                open_items.pop()
            elif token.type == "list_item_open" and token.map:
                line_num = token.map[0] + 1
                outer_items = open_items.count(line_num)
                open_items.append(line_num)
                if not list_stack:
                    continue

                list_type, is_multi = list_stack[-1]
                line_content = document.get_line(line_num)

                if line_content is None:
                    continue

                if list_type == "ul":
                    expected_spaces = config.ul_multi if is_multi else config.ul_single
                else:
                    expected_spaces = config.ol_multi if is_multi else config.ol_single

                match = find_list_marker(line_content, token, outer_items)
                # An empty item's marker can end the line; there is no spacing to check.
                if match and match.group("space") and len(match.group("space")) != expected_spaces:
                    yield _MarkerSpacing(
                        token, line_num, token.map[1], match, expected_spaces, outer_items, quotes
                    )

    def check(self, document: Document, config: MD030Config) -> list[Violation]:
        """Check for list marker spacing violations."""
        violations: list[Violation] = []

        for item in self._iter_violating_items(document, config):
            actual_spaces = len(item.match.group("space"))
            violations.append(
                Violation(
                    line=item.line,
                    column=item.match.end("marker") + 1,
                    rule_id=self.id,
                    rule_name=self.name,
                    message=(
                        f"Expected {item.expected} "
                        f"space{'s' if item.expected != 1 else ''} "
                        f"after list marker, found {actual_spaces}"
                    ),
                    context=document.get_line(item.line),
                )
            )

        return violations

    def fix(self, document: Document, config: MD030Config) -> str | None:
        """Fix list marker spacing by adjusting spaces after markers."""
        items_to_fix = list(self._iter_violating_items(document, config))
        if not items_to_fix:
            return None

        lines = document.content.split("\n")
        for item in items_to_fix:
            line = lines[item.line - 1]
            # Fixing an enclosing item may have shifted this line, so find the marker again.
            match = find_list_marker(line, item.token, item.outer_items)
            if not match:
                continue
            delta = item.expected - len(match.group("space"))
            lines[item.line - 1] = (
                line[: match.end("marker")] + " " * item.expected + line[match.end("space") :]
            )

            # Adjust indentation of continuation lines within this list item
            if delta != 0:
                for i in range(item.line, item.end_line):
                    lines[i] = self._shift_continuation(lines[i], item.quotes, delta)

        return "\n".join(lines)

    @staticmethod
    def _shift_continuation(line: str, quotes: int, delta: int) -> str:
        """Move a continuation line's content by delta columns to follow its item's marker.

        The shift happens after the enclosing blockquote markers, since moving the ``>``
        itself would take the line out of its quote.
        """
        pos = 0
        for _ in range(quotes):
            match = _QUOTE_MARKER.match(line, pos)
            if match is None:
                return line  # a lazy continuation line, whose indentation has no meaning
            pos = match.end()
        rest = line[pos:]
        if not rest.strip():
            return line
        if delta > 0:
            return line[:pos] + " " * delta + rest
        remove = min(-delta, len(rest) - len(rest.lstrip()))
        return line[:pos] + rest[remove:]

    @staticmethod
    def _analyze_lists(tokens: list, list_info: dict[int, bool]) -> None:
        """Analyze tokens to determine which lists have multi-paragraph items.

        A list is considered multi-paragraph if any of its items contain
        more than one block-level element (paragraph, sub-list, code block, etc.).
        """
        # Each entry: (token_index, has_multi_paragraph, item_block_count)
        stack: list[tuple[int, bool, int]] = []
        item_block_count = 0
        has_multi_paragraph = False

        for i, token in enumerate(tokens):
            if token.type in ("bullet_list_open", "ordered_list_open"):
                # Count sub-lists as block elements for the parent item
                item_block_count += 1
                stack.append((i, has_multi_paragraph, item_block_count))
                has_multi_paragraph = False
                item_block_count = 0
            elif token.type in ("bullet_list_close", "ordered_list_close"):
                if stack:
                    list_token_index, parent_has_multi, parent_block_count = stack.pop()
                    list_info[list_token_index] = has_multi_paragraph
                    has_multi_paragraph = parent_has_multi
                    item_block_count = parent_block_count
            elif token.type == "list_item_open":
                item_block_count = 0
            elif token.type == "list_item_close":
                if item_block_count > 1:
                    has_multi_paragraph = True
            elif token.type in (
                "paragraph_open",
                "code_block",
                "fence",
                "blockquote_open",
                "heading_open",
            ):
                item_block_count += 1
