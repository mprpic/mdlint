from dataclasses import dataclass, field

from markdown_it.token import Token

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD005Config(RuleConfig):
    """Configuration for MD005 rule."""


@dataclass
class _ListState:
    """Internal state for tracking a list's indentation."""

    is_ordered: bool
    expected_indent: int | None = None
    expected_end: int | None = None  # End column of marker (ordered lists only)
    end_matching: bool = False  # Whether right-alignment has been detected


@dataclass
class ListItem:
    """Where a list item's marker sits on its first line, measured inside its innermost quote.

    A blockquote's content starts a fresh column, so list indentation rules measure items
    from the innermost ``>`` (or the line start) rather than from column 0. MD005 and MD007
    share this so their checks and fixes agree on what an item's indentation is.
    """

    start: int  # 0-indexed first line
    end: int  # 0-indexed line after the last line of the item
    quotes: int  # number of enclosing blockquotes
    kinds: list[str]  # "bullet" or "ordered" per list inside the innermost quote, own list last
    list_id: int  # index of the token that opens the item's own list
    parent: "ListItem | None"  # enclosing item inside the same blockquote
    run_start: int  # index on the first line where the innermost quote's content run begins
    space: int  # 1 if the quote marker took the space that follows it
    marker_index: int
    marker: str
    width: int  # marker plus the whitespace up to the item's content
    tabbed: bool  # a tab in the indentation of the item or a parent, so columns != characters

    @property
    def leading(self) -> int:
        """Characters between the innermost ``>`` (or the line start) and the marker."""
        return self.marker_index - self.run_start

    @property
    def indent(self) -> int:
        """Columns between the start of the quote's content (or the line) and the marker."""
        return self.leading - self.space

    @property
    def content(self) -> int:
        """Column of the item's content, counted like ``indent``."""
        return self.indent + self.width


@dataclass
class _Scope:
    """Lists and items open inside one blockquote (or the document root)."""

    lists: list[int] = field(default_factory=list)
    items: list[ListItem | None] = field(default_factory=list)


def _run_start(document: Document, index: int, quotes: int) -> int | None:
    """Return where the content of the innermost of ``quotes`` blockquotes begins on a line.

    The index points just past that quote's ``>``. Returns None when the line does not carry
    all the markers (a lazy continuation line).
    """
    if quotes == 0:
        return 0
    prefix = document.container_prefix(index + 1)
    position = -1
    for _ in range(quotes):
        position = prefix.find(">", position + 1)
        if position < 0:
            return None
    return position + 1


def _measure(document: Document, token: Token, scope: _Scope, quotes: int) -> ListItem | None:
    if token.map is None or not scope.lists or token.map[0] >= len(document.lines):
        return None
    parent = scope.items[-1] if scope.items else None
    if scope.items and parent is None:
        return None  # nested in an item that could not be measured
    start = token.map[0]
    line = document.lines[start]
    run_start = _run_start(document, start, quotes)
    if run_start is None:
        return None
    space = 1 if quotes and line[run_start : run_start + 1] in (" ", "\t") else 0
    position = run_start
    if parent is not None and parent.start == start:
        position = parent.marker_index + len(parent.marker)
    marker_index = len(line) - len(line[position:].lstrip(" \t"))
    marker = token.info + token.markup
    if not line.startswith(marker, marker_index):
        return None
    after = line[marker_index + len(marker) :]
    gap = len(after) - len(after.lstrip(" \t"))
    # Per CommonMark, a blank first line or 5+ spaces put the content one column after the marker.
    width = len(marker) + (1 if gap == len(after) or gap >= 5 else gap)
    tabbed = (parent is not None and parent.tabbed) or "\t" in line[: len(line) - len(after) + gap]
    for other in document.lines[start + 1 : token.map[1]]:
        tabbed = tabbed or "\t" in other[: len(other) - len(other.lstrip(" \t>"))]
    return ListItem(
        start=start,
        end=token.map[1],
        quotes=quotes,
        kinds=[document.tokens[i].type.split("_")[0] for i in scope.lists],
        list_id=scope.lists[-1],
        parent=parent,
        run_start=run_start,
        space=space,
        marker_index=marker_index,
        marker=marker,
        width=width,
        tabbed=tabbed,
    )


def scan_list_items(document: Document) -> list[ListItem]:
    """Measure every list item in document order.

    Items whose position cannot be determined (for example tab-indented markers), and items
    nested in them, are left out.
    """
    items: list[ListItem] = []
    scopes = [_Scope()]
    for index, token in enumerate(document.tokens):
        scope = scopes[-1]
        if token.type == "blockquote_open":
            scopes.append(_Scope())
        elif token.type == "blockquote_close":
            scopes.pop()
        elif token.type in ("bullet_list_open", "ordered_list_open"):
            scope.lists.append(index)
        elif token.type in ("bullet_list_close", "ordered_list_close"):
            scope.lists.pop()
        elif token.type == "list_item_open":
            item = _measure(document, token, scope, len(scopes) - 1)
            scope.items.append(item)
            if item is not None:
                items.append(item)
        elif token.type == "list_item_close":
            scope.items.pop()
    return items


def can_reindent(item: ListItem, indent: int, parent_shift: int = 0) -> bool:
    """Whether moving the item's marker to ``indent`` keeps it a child of the same parent.

    ``parent_shift`` is how far the parent itself moves. Fewer columns than the parent's
    content would make the item a sibling of its parent, and four or more beyond it would
    turn it into an indented code block. Tab indentation is never moved, because character
    offsets no longer match columns there.
    """
    if item.tabbed:
        return False
    if item.parent is None:
        return 0 <= indent <= 3
    if item.parent.start == item.start:
        return False  # moving it would change the parent's marker width instead
    return 0 <= indent - (item.parent.content + parent_shift) <= 3


def shift_list_items(document: Document, shifts: list[tuple[ListItem, int, int]]) -> str | None:
    """Move list items sideways, each together with every line it owns.

    Each shift is (item, characters to add or remove before the marker, columns to add or
    remove on the item's other lines). Shifting only the marker line would leave
    continuation lines, nested lists and code inside the item at their old indentation,
    which detaches them from the item or changes code block contents. Shifts of nested items
    add up. Blank and lazy continuation lines are left alone: they are not indented into the
    item, so their indentation carries no structure.
    """
    edits: dict[tuple[int, int], int] = {}
    for item, marker_delta, content_delta in shifts:
        if marker_delta:
            key = (item.start, item.run_start)
            edits[key] = edits.get(key, 0) + marker_delta
        if not content_delta:
            continue
        for index in range(item.start + 1, min(item.end, len(document.lines))):
            run_start = _run_start(document, index, item.quotes)
            if run_start is None:
                continue
            rest = document.lines[index][run_start:]
            whitespace = len(rest) - len(rest.lstrip(" \t"))
            space = 1 if item.quotes and whitespace else 0
            if whitespace - space < item.content:
                continue
            key = (index, run_start)
            edits[key] = edits.get(key, 0) + content_delta

    lines = document.content.split("\n")
    changed = False
    for (index, position), delta in sorted(edits.items(), reverse=True):
        line = lines[index]
        if delta > 0:
            lines[index] = line[:position] + " " * delta + line[position:]
        elif delta < 0:
            rest = line[position:]
            whitespace = len(rest) - len(rest.lstrip(" \t"))
            lines[index] = line[:position] + rest[min(-delta, whitespace) :]
        changed = changed or delta != 0
    return "\n".join(lines) if changed else None


class MD005(Rule[MD005Config]):
    """List item indentation should be consistent."""

    id = "MD005"
    name = "list-indent"
    summary = "List item indentation should be consistent"
    config_class = MD005Config
    preserves_rendering = True

    description = (
        "This rule detects when list items within the same list have "
        "inconsistent indentation. Each list is checked independently; "
        "separate lists in the same document do not affect each other. "
        "Both ordered and unordered lists are checked. For ordered lists, "
        "right-aligned markers are accepted (e.g., when items 9 and 10 "
        "have different leading spaces but their markers end at the same column). "
        "Inside a blockquote, indentation is counted from the `>` marker. "
        "The fix moves each misaligned item together with its continuation "
        "lines, nested lists, and code blocks."
    )

    rationale = (
        "Inconsistent indentation can lead to improperly rendered content. "
        "Even small differences in spacing may cause Markdown parsers to "
        "interpret list structure differently than intended, resulting in "
        "incorrect nesting or broken lists in the final output."
    )

    example_valid = """\
# Consistent Indentation

- Item 1
  - Nested item 1
  - Nested item 2
    - Deep nested 1
    - Deep nested 2
- Item 2
  - Nested under 2
"""

    example_invalid = """\
# Inconsistent Indentation

- Item 1
  - Nested with 2 spaces
   - Nested with 3 spaces
"""

    def check(self, document: Document, config: MD005Config) -> list[Violation]:
        """Check for inconsistent list indentation."""
        return [
            Violation(
                line=item.start + 1,
                column=item.marker_index + 1,
                rule_id=self.id,
                rule_name=self.name,
                message=message,
                context=document.lines[item.start],
            )
            for item, _, message in self._misaligned_items(document)
        ]

    def fix(self, document: Document, config: MD005Config) -> str | None:
        """Fix inconsistent list indentation by moving each misaligned item as a whole."""
        shifts: list[tuple[ListItem, int, int]] = []
        for item, expected, _ in self._misaligned_items(document):
            # Inside a quote, the first space after `>` belongs to the quote marker.
            new_indent = expected - (1 if item.quotes and expected > 0 else 0)
            if can_reindent(item, new_indent):
                shifts.append((item, expected - item.leading, new_indent - item.indent))
        return shift_list_items(document, shifts)

    def _misaligned_items(self, document: Document) -> list[tuple[ListItem, int, str]]:
        """Return (item, expected leading width, message) for each misaligned item."""
        results: list[tuple[ListItem, int, str]] = []
        states: dict[int, _ListState] = {}
        for item in scan_list_items(document):
            is_ordered = item.kinds[-1] == "ordered"
            state = states.setdefault(item.list_id, _ListState(is_ordered=is_ordered))
            if is_ordered:
                result = self._check_ordered_item(state, item.leading, len(item.marker))
            else:
                result = self._check_unordered_item(state, item.leading)
            if result is not None:
                results.append((item, *result))
        return results

    @staticmethod
    def _check_unordered_item(state: _ListState, indent: int) -> tuple[int, str] | None:
        if state.expected_indent is None:
            state.expected_indent = indent
            return None

        if state.expected_indent != indent:
            return state.expected_indent, f"Expected {state.expected_indent} spaces, found {indent}"
        return None

    @staticmethod
    def _check_ordered_item(
        state: _ListState, indent: int, marker_len: int
    ) -> tuple[int, str] | None:
        actual_end = indent + marker_len

        if state.expected_indent is None or state.expected_end is None:
            state.expected_indent = indent
            state.expected_end = actual_end
            return None

        if state.expected_indent != indent or state.end_matching:
            if state.expected_end == actual_end:
                state.end_matching = True
                return None

            if state.end_matching:
                # Right-aligned: move the marker so it ends where the others end
                return (
                    max(0, state.expected_end - marker_len),
                    f"Expected marker end at column {state.expected_end}, "
                    f"found column {actual_end}",
                )

            return state.expected_indent, f"Expected {state.expected_indent} spaces, found {indent}"

        return None
