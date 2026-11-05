from dataclasses import dataclass, field

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.rules.md005 import ListItem, can_reindent, scan_list_items, shift_list_items
from mdlint.violation import Violation


@dataclass
class MD007Config(RuleConfig):
    """Configuration for MD007 rule."""

    indent: int = field(
        default=2,
        metadata={
            "description": "Number of spaces for each indentation level.",
        },
    )
    start_indented: bool = field(
        default=False,
        metadata={
            "description": "Whether top-level lists can be indented.",
        },
    )
    start_indent: int | None = field(
        default=None,
        metadata={
            "description": (
                "Number of spaces for first-level indentation when start_indented is "
                "True. Defaults to the value of indent."
            ),
        },
    )

    def __post_init__(self) -> None:
        if self.start_indent is None:
            self.start_indent = self.indent


class MD007(Rule[MD007Config]):
    """Unordered list indentation."""

    id = "MD007"
    name = "ul-indent"
    summary = "Unordered list indentation"
    config_class = MD007Config

    description = (
        "This rule enforces consistent indentation for nested unordered list "
        "items. It triggers when list items are not indented by the configured "
        "number of spaces (default: 2). This rule only applies to a sublist "
        "whose parent lists are all also unordered. A blockquote starts a new "
        "top level: lists inside it are measured from the `>` marker, and lists "
        "outside it do not count as parents. The fix moves each item together "
        "with its continuation lines, nested lists, and code blocks."
    )

    rationale = (
        "Consistent indentation improves readability and ensures Markdown "
        "documents render correctly across different parsers. Inconsistent "
        "indentation can cause compatibility issues, as some parsers require "
        "specific indent amounts."
    )

    example_valid = """\
# Valid Unordered List Indentation

- Item 1
  - Nested item (2 spaces)
  - Another nested item
    - Deep nested item (4 spaces total)
    - Another deep item
- Item 2
  - Nested under 2
"""

    example_invalid = """\
# Invalid Unordered List Indentation

- Item 1
   - Nested item (3 spaces instead of 2)
- Item 2
    - Nested with 4 spaces instead of 2
"""

    def check(self, document: Document, config: MD007Config) -> list[Violation]:
        """Check for unordered list indentation violations."""
        return [
            Violation(
                line=item.start + 1,
                column=1,
                rule_id=self.id,
                rule_name=self.name,
                message=f"Expected {expected} spaces, found {item.indent}",
                context=document.lines[item.start],
            )
            for item, expected in self._expected_indents(document, config)
            if expected is not None and item.indent != expected
        ]

    def fix(self, document: Document, config: MD007Config) -> str | None:
        """Fix unordered list indentation by moving each item as a whole."""
        items = self._expected_indents(document, config)
        # Siblings move together: if one item of a list cannot move, moving the others would
        # change which item contains which, so that whole list stays where it is.
        frozen_lists: set[int] = set()
        while (shifts := self._plan_shifts(items, frozen_lists)) is None:
            pass
        return shift_list_items(document, shifts)

    @staticmethod
    def _plan_shifts(
        items: list[tuple[ListItem, int | None]], frozen_lists: set[int]
    ) -> list[tuple[ListItem, int, int]] | None:
        """Plan each item's move, or freeze the first list with an item that cannot move.

        Returns None after adding a list to ``frozen_lists``, so the caller plans again.
        """
        # Expected indents are absolute, but shifts of nested items add up, so each item
        # only moves by what its parent's shift has not already done.
        moved: dict[int, int] = {}
        shifts: list[tuple[ListItem, int, int]] = []
        for item, expected in items:
            inherited = moved[id(item.parent)] if item.parent else 0
            target = item.indent + inherited
            if expected is not None and expected != target and item.list_id not in frozen_lists:
                if not can_reindent(item, expected, inherited):
                    frozen_lists.add(item.list_id)
                    return None
                target = expected
            moved[id(item)] = target - item.indent
            own = target - item.indent - inherited
            if own:
                # A quote marker with no space after it takes the first inserted space.
                gap = 1 if item.quotes and item.leading == 0 and own > 0 else 0
                shifts.append((item, own + gap, own))
        return shifts

    @staticmethod
    def _expected_indents(
        document: Document, config: MD007Config
    ) -> list[tuple[ListItem, int | None]]:
        """Pair each list item with its expected indent, or None if the rule skips it."""
        # __post_init__ guarantees start_indent is resolved to int
        start_indent: int = config.start_indent  # type: ignore[assignment]
        base = start_indent if config.start_indented else 0
        results: list[tuple[ListItem, int | None]] = []
        for item in scan_list_items(document):
            expected = None
            # Only lists whose parents inside the same blockquote are all unordered
            if "ordered" not in item.kinds:
                expected = base + (len(item.kinds) - 1) * config.indent
            results.append((item, expected))
        return results
