from collections.abc import Iterator
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

Links with inline code [`TextArea` documentation](https://example.com/) are fine.

Reference links [like this][ref] are also fine.

[ref]: https://example.com/reference
"""

    example_invalid = """\
# Links with Spaces

This is a [ link with leading space](https://www.example.com/).

Here is [link with trailing space ](https://example.org/page) in a sentence.

And [ spaces on both sides ](https://example.net/) is also wrong.
"""

    def _find_spaced_links(self, document: Document) -> Iterator[tuple[int, int, str, bool, bool]]:
        """Find links with leading/trailing spaces in link text.

        Yields tuples of (line_num, column, raw_text, has_leading, has_trailing)
        for each link with spacing issues.
        """
        for token in document.tokens:
            if token.type != "inline" or not token.children or not token.map:
                continue

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
                        elif child.type == "image":
                            alt = child.content or ""
                            src = child.attrGet("src") or ""
                            title = child.attrGet("title")
                            if title:
                                raw_parts.append(f'![{alt}]({src} "{title}")')
                            else:
                                raw_parts.append(f"![{alt}]({src})")
                        i += 1

                    raw_text = "".join(raw_parts)
                    target = "[" + raw_text + "]"
                    idx = source.find(target, search_offset)
                    # Skip image brackets (preceded by !)
                    while idx > 0 and source[idx - 1] == "!":
                        idx = source.find(target, idx + 1)

                    if idx < 0:
                        i += 1
                        continue

                    line_num, column = self._source_idx_to_position(idx, source_lines)
                    search_offset = idx + len(target)

                    if raw_text:
                        has_leading = raw_text != raw_text.lstrip(" ")
                        has_trailing = raw_text != raw_text.rstrip(" ")

                        if has_leading or has_trailing:
                            yield line_num, column, raw_text, has_leading, has_trailing

                i += 1

    def check(self, document: Document, config: MD039Config) -> list[Violation]:
        """Check for spaces inside link text."""
        violations: list[Violation] = []

        for line_num, column, _, has_leading, has_trailing in self._find_spaced_links(document):
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

        return violations

    def fix(self, document: Document, config: MD039Config) -> str | None:
        """Fix spaces inside link text by stripping leading/trailing spaces."""
        replacements: dict[int, list[tuple[str, str]]] = {}

        for line_num, _, raw_text, _, _ in self._find_spaced_links(document):
            target = "[" + raw_text + "]"
            new_target = "[" + raw_text.strip() + "]"
            replacements.setdefault(line_num, []).append((target, new_target))

        if not replacements:
            return None

        lines = document.content.split("\n")
        for line_num, line_replacements in replacements.items():
            line = lines[line_num - 1]
            for old, new in line_replacements:
                line = line.replace(old, new, 1)
            lines[line_num - 1] = line

        return "\n".join(lines)

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
