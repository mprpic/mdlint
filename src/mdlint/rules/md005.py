from dataclasses import dataclass

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


class MD005(Rule[MD005Config]):
    """List item indentation should be consistent."""

    id = "MD005"
    name = "list-indent"
    summary = "List item indentation should be consistent"
    config_class = MD005Config

    description = (
        "This rule detects when list items within the same list have "
        "inconsistent indentation. Each list is checked independently; "
        "separate lists in the same document do not affect each other. "
        "Both ordered and unordered lists are checked. For ordered lists, "
        "right-aligned markers are accepted (e.g., when items 9 and 10 "
        "have different leading spaces but their markers end at the same column)."
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
        violations: list[Violation] = []
        list_stack: list[_ListState] = []

        for token in document.tokens:
            if token.type in ("bullet_list_open", "ordered_list_open"):
                list_stack.append(_ListState(is_ordered=(token.type == "ordered_list_open")))
            elif token.type in ("bullet_list_close", "ordered_list_close"):
                if list_stack:
                    list_stack.pop()
            elif token.type == "list_item_open" and token.map and list_stack:
                line_num = token.map[0] + 1
                line_content = document.get_line(line_num)

                if line_content is None:
                    continue

                indent = len(line_content) - len(line_content.lstrip())
                current_list = list_stack[-1]

                if current_list.is_ordered:
                    violation = self._check_ordered_item(
                        current_list, indent, line_content, line_num
                    )
                else:
                    violation = self._check_unordered_item(
                        current_list, indent, line_content, line_num
                    )

                if violation:
                    violations.append(violation)

        return violations

    def _check_unordered_item(
        self,
        state: _ListState,
        indent: int,
        line_content: str,
        line_num: int,
    ) -> Violation | None:
        if state.expected_indent is None:
            state.expected_indent = indent
            return None

        if state.expected_indent != indent:
            return Violation(
                line=line_num,
                column=indent + 1,
                rule_id=self.id,
                rule_name=self.name,
                message=f"Expected {state.expected_indent} spaces, found {indent}",
                context=line_content,
            )
        return None

    def _check_ordered_item(
        self,
        state: _ListState,
        indent: int,
        line_content: str,
        line_num: int,
    ) -> Violation | None:
        marker_len = self._get_marker_length(line_content)
        actual_end = indent + marker_len

        if state.expected_indent is None:
            state.expected_indent = indent
            state.expected_end = actual_end
            return None

        if state.expected_indent != indent or state.end_matching:
            if state.expected_end == actual_end:
                state.end_matching = True
                return None

            if state.end_matching:
                message = (
                    f"Expected marker end at column {state.expected_end}, found column {actual_end}"
                )
            else:
                message = f"Expected {state.expected_indent} spaces, found {indent}"

            return Violation(
                line=line_num,
                column=indent + 1,
                rule_id=self.id,
                rule_name=self.name,
                message=message,
                context=line_content,
            )

        return None

    @staticmethod
    def _get_marker_length(line: str) -> int:
        """Get the length of an ordered list marker (e.g., '1.' returns 2, '10.' returns 3)."""
        stripped = line.lstrip()
        for i, char in enumerate(stripped):
            if char in ".)":
                return i + 1
            if not char.isdigit():
                return 0
        return 0
