import re
from dataclasses import dataclass, field

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
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
        "whose parent lists are all also unordered."
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

    BLOCKQUOTE_PREFIX_RE = re.compile(r"^([ \t]*>[ \t]?)+")

    def check(self, document: Document, config: MD007Config) -> list[Violation]:
        """Check for unordered list indentation violations."""
        violations: list[Violation] = []

        indent = config.indent
        start_indented = config.start_indented
        # __post_init__ guarantees start_indent is resolved to int
        start_indent: int = config.start_indent  # type: ignore[assignment]

        # Track list nesting: stack of list types ("bullet" or "ordered")
        list_stack: list[str] = []
        blockquote_depth = 0

        for token in document.tokens:
            if token.type == "blockquote_open":
                blockquote_depth += 1
            elif token.type == "blockquote_close":
                blockquote_depth -= 1
            elif token.type == "bullet_list_open":
                list_stack.append("bullet")
            elif token.type == "ordered_list_open":
                list_stack.append("ordered")
            elif token.type in ("bullet_list_close", "ordered_list_close"):
                if list_stack:
                    list_stack.pop()
            elif token.type == "list_item_open" and token.map:
                # Only check items in bullet lists where all parents are also bullet
                if not list_stack or list_stack[-1] != "bullet":
                    continue

                # Check if all ancestors are bullet lists
                if "ordered" in list_stack:
                    continue

                line_num = token.map[0] + 1
                line_content = document.get_line(line_num)

                if line_content is None:
                    continue

                # Strip blockquote prefix before measuring indentation
                if blockquote_depth > 0:
                    match = self.BLOCKQUOTE_PREFIX_RE.match(line_content)
                    if match:
                        line_content = line_content[match.end() :]

                # Calculate actual indentation
                actual_indent = len(line_content) - len(line_content.lstrip())

                # Calculate expected indentation based on nesting level
                nesting_level = len(list_stack) - 1  # 0-indexed depth

                base = start_indent if start_indented else 0
                expected_indent = base + nesting_level * indent

                if actual_indent != expected_indent:
                    violations.append(
                        Violation(
                            line=line_num,
                            column=1,
                            rule_id=self.id,
                            rule_name=self.name,
                            message=(f"Expected {expected_indent} spaces, found {actual_indent}"),
                            context=line_content,
                        )
                    )

        return violations
