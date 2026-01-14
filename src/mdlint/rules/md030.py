import re
from dataclasses import dataclass, field

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


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


class MD030(Rule[MD030Config]):
    """Spaces after list markers."""

    id = "MD030"
    name = "list-marker-space"
    summary = "Spaces after list markers"
    config_class = MD030Config

    description = (
        "This rule checks the number of spaces between list markers "
        "(such as -, *, +, or 1.) and the text of list items. It supports "
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

    # Regex patterns for extracting spaces after list markers
    UL_PATTERN = re.compile(r"^(\s*)([*+-])(\s+)")
    OL_PATTERN = re.compile(r"^(\s*)(\d+\.)(\s+)")

    def check(self, document: Document, config: MD030Config) -> list[Violation]:
        """Check for list marker spacing violations."""
        violations: list[Violation] = []

        # Track list context: stack of (list_type, is_multi_paragraph)
        list_stack: list[tuple[str, bool]] = []

        # First pass: identify which lists have multi-paragraph items
        list_info: dict[int, bool] = {}  # token index -> is_multi_paragraph
        self._analyze_lists(document.tokens, list_info)

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
            elif token.type == "list_item_open" and token.map:
                if not list_stack:
                    continue

                list_type, is_multi = list_stack[-1]
                line_num = token.map[0] + 1
                line_content = document.get_line(line_num)

                if line_content is None:
                    continue

                # Determine expected spaces based on list type and multi-paragraph
                if list_type == "ul":
                    expected_spaces = config.ul_multi if is_multi else config.ul_single
                    pattern = self.UL_PATTERN
                else:
                    expected_spaces = config.ol_multi if is_multi else config.ol_single
                    pattern = self.OL_PATTERN

                match = pattern.match(line_content)
                if match:
                    actual_spaces = len(match.group(3))
                    if actual_spaces != expected_spaces:
                        # Calculate column (after marker)
                        marker_end = match.end(2)
                        violations.append(
                            Violation(
                                line=line_num,
                                column=marker_end + 1,
                                rule_id=self.id,
                                rule_name=self.name,
                                message=(
                                    f"Expected {expected_spaces} "
                                    f"space{'s' if expected_spaces != 1 else ''} "
                                    f"after list marker, found {actual_spaces}"
                                ),
                                context=line_content,
                            )
                        )

        return violations

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
