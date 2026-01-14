from dataclasses import dataclass

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD039Config(RuleConfig):
    """Configuration for MD039 rule."""


class MD039(Rule[MD039Config]):
    """Spaces inside link text."""

    id = "MD039"
    name = "no-space-in-links"
    summary = "Spaces inside link text"
    config_class = MD039Config

    description = (
        "This rule is triggered when a link contains spaces at the beginning "
        "or end of the link text. The link text is the portion inside the "
        "square brackets."
    )

    rationale = (
        "Consistent formatting makes it easier to understand a document. "
        "Spaces at the beginning or end of link text are usually accidental "
        "and can look awkward when rendered."
    )

    example_valid = """\
# Valid Links

This is a [properly formatted link](https://www.example.com/).

Here is [another link](https://example.org/page) in a sentence.

Reference links [like this][ref] are also fine.

[ref]: https://example.com/reference
"""

    example_invalid = """\
# Links with Spaces

This is a [ link with leading space](https://www.example.com/).

Here is [link with trailing space ](https://example.org/page) in a sentence.

And [ spaces on both sides ](https://example.net/) is also wrong.
"""

    def check(self, document: Document, config: MD039Config) -> list[Violation]:
        """Check for spaces inside link text."""
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
                    i += 1
                    first_text = None
                    last_text = None
                    raw_parts: list[str] = []

                    while i < len(children) and children[i].type != "link_close":
                        child = children[i]
                        if child.type == "text":
                            if first_text is None:
                                first_text = child
                            last_text = child
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
                        line_num, column = self._source_idx_to_position(idx, source_lines)
                        search_offset = idx + len(target)
                    else:
                        line_num = token.map[0] + 1
                        column = 1

                    if first_text is not None:
                        has_leading = first_text.content != first_text.content.lstrip()
                        has_trailing = (
                            last_text is not None
                            and last_text.content != last_text.content.rstrip()
                        )
                        context = document.get_line(line_num)

                        if has_leading:
                            violations.append(
                                Violation(
                                    line=line_num,
                                    column=column,
                                    rule_id=self.id,
                                    rule_name=self.name,
                                    message="Link text has leading space(s)",
                                    context=context,
                                )
                            )

                        if has_trailing:
                            violations.append(
                                Violation(
                                    line=line_num,
                                    column=column,
                                    rule_id=self.id,
                                    rule_name=self.name,
                                    message="Link text has trailing space(s)",
                                    context=context,
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
