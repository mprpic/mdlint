from dataclasses import dataclass

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD032Config(RuleConfig):
    """Configuration for MD032 rule."""


class MD032(Rule[MD032Config]):
    """Lists should be surrounded by blank lines."""

    id = "MD032"
    name = "blanks-around-lists"
    summary = "Lists should be surrounded by blank lines"
    config_class = MD032Config

    description = (
        "This rule enforces blank lines around lists. It triggers when "
        "lists (ordered or unordered) are not preceded or followed by a "
        "blank line. The first list in a document does not require a blank "
        "line above, and the last list at the end of a document does not "
        "require a blank line below."
    )

    rationale = (
        "Aside from aesthetic reasons, some Markdown parsers require a blank line before a list "
        "when it follows a paragraph, or the list items may be treated as plain text."
    )

    example_valid = """\
Some text here.

* Item 1
* Item 2
* Item 3

More text here.

1. First
2. Second
3. Third

Final text.
"""

    example_invalid = """\
Some text here.
* Item 1
* Item 2
* Item 3

1. First
2. Second
3. Third
# More text here.
"""

    def _get_list_ranges(self, document: Document) -> list[tuple[int, int]]:
        """Return top-level list ranges as 1-indexed (start, end) tuples.

        markdown-it-py splits lists with mixed markers into separate
        tokens; merge consecutive ranges so they are treated as one list.
        """
        list_ranges: list[tuple[int, int]] = []
        nesting = 0

        for token in document.tokens:
            if token.type in ("bullet_list_open", "ordered_list_open"):
                if nesting == 0 and token.map:
                    list_start = token.map[0] + 1  # 1-indexed
                    list_end = token.map[1]  # 1-indexed last line

                    # Merge with previous range if they are adjacent
                    if list_ranges:
                        prev_start, prev_end = list_ranges[-1]
                        if prev_end + 1 >= list_start:
                            list_ranges[-1] = (prev_start, max(prev_end, list_end))
                        else:
                            list_ranges.append((list_start, list_end))
                    else:
                        list_ranges.append((list_start, list_end))

                nesting += 1
            elif token.type in ("bullet_list_close", "ordered_list_close"):
                nesting -= 1

        return list_ranges

    def check(self, document: Document, config: MD032Config) -> list[Violation]:
        """Check for blanks-around-lists violations."""
        violations: list[Violation] = []

        for list_start, list_end in self._get_list_ranges(document):
            # Check blank line above
            if list_start > 1:
                line_above = document.get_line(list_start - 1)
                if line_above is not None and line_above.strip() != "":
                    violations.append(
                        Violation(
                            line=list_start,
                            column=1,
                            rule_id=self.id,
                            rule_name=self.name,
                            message="Expected blank line above list",
                            context=document.get_line(list_start),
                        )
                    )

            # Check blank line below
            # List token maps may include a trailing blank line in
            # their range; if the last mapped line is already blank,
            # no violation is possible.
            last_line = document.get_line(list_end)
            if last_line is not None and last_line.strip() != "" and list_end < len(document.lines):
                line_below = document.get_line(list_end + 1)
                if line_below is not None and line_below.strip() != "":
                    violations.append(
                        Violation(
                            line=list_end,
                            column=1,
                            rule_id=self.id,
                            rule_name=self.name,
                            message="Expected blank line below list",
                            context=last_line,
                        )
                    )

        return violations

    def fix(self, document: Document, config: MD032Config) -> str | None:
        """Fix blanks-around-lists violations by inserting missing blank lines."""
        list_ranges = self._get_list_ranges(document)
        if not list_ranges:
            return None

        lines = document.content.split("\n")
        num_doc_lines = len(document.lines)
        changed = False

        # Process lists from bottom to top so insertions don't shift indices
        for list_start, list_end in reversed(list_ranges):
            # list_start/list_end are 1-indexed

            # Fix blank line below: list token maps may include a trailing
            # blank line; only check below if the last mapped line is non-blank.
            last_line = document.get_line(list_end)
            if last_line is not None and last_line.strip() != "" and list_end < num_doc_lines:
                if lines[list_end].strip() != "":
                    lines.insert(list_end, "")
                    changed = True

            # Fix blank line above
            if list_start > 1 and lines[list_start - 2].strip() != "":
                lines.insert(list_start - 1, "")
                changed = True

        if not changed:
            return None

        return "\n".join(lines)
