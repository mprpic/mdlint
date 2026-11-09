from dataclasses import dataclass
from pathlib import Path

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD027Config(RuleConfig):
    """Configuration for MD027 rule."""


class MD027(Rule[MD027Config]):
    """Multiple spaces after blockquote symbol."""

    id = "MD027"
    name = "no-multiple-space-blockquote"
    summary = "Multiple spaces after blockquote symbol"
    config_class = MD027Config
    preserves_rendering = True

    description = (
        "This rule is triggered when blockquote lines contain more than one "
        "space after the blockquote marker (`>`). The standard format requires "
        "exactly one space between the `>` and the content. Indentation that "
        "belongs to a list inside the blockquote is not flagged; MD005 and "
        "MD007 check it. The fix leaves a line unchanged when removing the "
        "spaces would turn it into a different block, such as a heading "
        "underline."
    )

    rationale = (
        "Extra space has no purpose and does not affect the rendering of "
        "content. Using a single space keeps the source clean and consistent."
    )

    example_valid = """\
> This is a blockquote with correct
> indentation.
"""

    example_invalid = """\
>  This is a blockquote with bad indentation
>  there should only be one.
"""

    def _find_multiple_space_lines(self, document: Document) -> list[tuple[int, int, int]]:
        """Return (line number, column of the `>`, end of the extra spaces) per offending line."""
        skipped = document.code_block_lines | document.html_block_lines
        results: list[tuple[int, int, int]] = []

        for line_num, line in enumerate(document.lines, start=1):
            if line_num in skipped:
                continue
            prefix = document.container_prefix(line_num)
            marker = prefix.rfind(">")
            # Only whitespace right after a quote marker counts; a list item opened inside
            # the quote owns the indentation that follows it.
            if marker < 0 or len(prefix) - marker > 2:
                continue
            rest = line[len(prefix) :]
            text = rest.lstrip(" \t")
            if text and len(text) < len(rest):
                results.append((line_num, marker + 1, len(line) - len(text)))

        return results

    def check(self, document: Document, config: MD027Config) -> list[Violation]:
        """Check for multiple spaces after blockquote marker."""
        return [
            Violation(
                line=line_num,
                column=marker + 1,
                rule_id=self.id,
                rule_name=self.name,
                message="Multiple spaces after blockquote symbol",
                context=document.get_line(line_num),
            )
            for line_num, marker, _ in self._find_multiple_space_lines(document)
        ]

    def fix(self, document: Document, config: MD027Config) -> str | None:
        """Fix multiple spaces after blockquote marker by collapsing to one."""
        lines = document.content.split("\n")
        changed = False
        for line_num, marker, end in self._find_multiple_space_lines(document):
            line = lines[line_num - 1]
            prefix_end = len(document.container_prefix(line_num))
            if self._changes_block(line[prefix_end:], line[end:]):
                continue
            lines[line_num - 1] = line[:prefix_end] + line[end:]
            changed = True

        return "\n".join(lines) if changed else None

    @staticmethod
    def _changes_block(indented: str, dedented: str) -> bool:
        """Whether dropping the indentation turns a line into a different kind of block.

        A line indented four or more columns past the quote is paragraph text even when it
        reads like ``---`` or ``# x``; without the indentation it would interrupt the
        paragraph, for example turning it into a setext heading. Both versions are parsed
        after a paragraph line, which is the only context where such a line survives
        outside a code block.
        """

        def shape(line: str) -> list[tuple[str, list[int] | None]]:
            tokens = Document(Path("<stdin>"), f"x\n{line}\n").tokens
            return [(token.type, token.map) for token in tokens]

        return shape(indented) != shape(dedented)
