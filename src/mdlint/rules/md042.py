from dataclasses import dataclass

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD042Config(RuleConfig):
    """Configuration for MD042 rule."""


class MD042(Rule[MD042Config]):
    """No empty links."""

    id = "MD042"
    name = "no-empty-links"
    summary = "No empty links"
    config_class = MD042Config

    description = (
        "This rule is triggered when an empty link is encountered. Empty links "
        "have no destination or contain only an empty fragment (#). This applies "
        "to inline links, as well as full, collapsed, and shortcut reference "
        "links whose definition points to an empty destination. Links must have "
        "a valid destination to function properly."
    )

    rationale = (
        "Empty links do not lead anywhere and therefore don't function as links. "
        "They may indicate incomplete content or a placeholder that was never "
        "filled in."
    )

    example_valid = """\
# Valid Links

This is a [proper link](https://example.com/).

This is a [fragment link](#section).

Here is a [reference link][ref].

[ref]: https://example.com/reference
"""

    example_invalid = """\
# Empty Links

This is an [empty link]().

This is an [empty fragment](#).

Here is [another empty]( ).
"""

    def check(self, document: Document, config: MD042Config) -> list[Violation]:
        """Check for empty links."""
        violations: list[Violation] = []

        for token in document.tokens:
            if token.type != "inline" or not token.children or not token.map:
                continue

            # Build source text for this inline token to find positions
            source_lines: list[tuple[int, str]] = []
            for ln in range(token.map[0] + 1, token.map[1] + 1):
                source_lines.append((ln, document.get_line(ln) or ""))
            source = "\n".join(line for _, line in source_lines)
            search_offset = 0

            children = token.children
            i = 0
            while i < len(children):
                if children[i].type == "link_open":
                    href = children[i].attrs.get("href", "") if children[i].attrs else ""

                    # Collect link text for position finding
                    i += 1
                    raw_parts: list[str] = []
                    while i < len(children) and children[i].type != "link_close":
                        child = children[i]
                        if child.type == "text":
                            raw_parts.append(child.content)
                        elif child.type in (
                            "em_open",
                            "em_close",
                            "strong_open",
                            "strong_close",
                        ):
                            raw_parts.append(child.markup)
                        elif child.type == "code_inline":
                            raw_parts.append(child.markup + child.content + child.markup)
                        elif child.type == "softbreak":
                            raw_parts.append("\n")
                        elif child.type == "html_inline":
                            raw_parts.append(child.content)
                        i += 1

                    # Find this link's position in source
                    raw_text = "".join(raw_parts)
                    target = "[" + raw_text + "]"
                    idx = source.find(target, search_offset)
                    # Skip image brackets (preceded by !)
                    while idx > 0 and source[idx - 1] == "!":
                        idx = source.find(target, idx + 1)
                    if idx >= 0:
                        search_offset = idx + len(target)

                    if href == "" or href == "#":
                        if idx >= 0:
                            line_num, column = self._source_idx_to_position(idx, source_lines)
                        else:
                            line_num = token.map[0] + 1
                            column = 1

                        violations.append(
                            Violation(
                                line=line_num,
                                column=column,
                                rule_id=self.id,
                                rule_name=self.name,
                                message="Empty link destination",
                                context=document.get_line(line_num),
                            )
                        )

                i += 1

        return violations

    @staticmethod
    def _source_idx_to_position(idx: int, source_lines: list[tuple[int, str]]) -> tuple[int, int]:
        """Convert a 0-indexed position in concatenated source to (line_num, column).

        Args:
            idx: 0-indexed position in the concatenated source string.
            source_lines: List of (1-indexed line number, line content) tuples.

        Returns:
            Tuple of (1-indexed line number, 1-indexed column).
        """
        current = 0
        for line_num, line in source_lines:
            line_end = current + len(line)
            if idx < line_end:
                return line_num, idx - current + 1
            current = line_end + 1  # +1 for the \n separator
        return source_lines[-1][0], 1
