from dataclasses import dataclass

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD028Config(RuleConfig):
    """Configuration for MD028 rule."""


class MD028(Rule[MD028Config]):
    """Blank line inside blockquote."""

    id = "MD028"
    name = "no-blanks-blockquote"
    summary = "Blank line inside blockquote"
    config_class = MD028Config

    description = (
        "This rule detects when two blockquote sections are separated only by "
        "blank lines, without any intervening text. This creates ambiguous "
        "Markdown that may be parsed differently by different implementations."
    )

    rationale = (
        "Some Markdown parsers will treat two blockquotes separated by one or "
        "more blank lines as the same blockquote, while others will treat them "
        "as separate blockquotes. To avoid ambiguity, either add text between "
        "blockquotes to clearly separate them, or use the blockquote marker (`>`) "
        "on blank lines to explicitly continue the same blockquote."
    )

    example_valid = """\
> This is a blockquote.

And Jimmy also said:

> This too is a blockquote.
"""

    example_invalid = """\
> This is a blockquote
> which is immediately followed by

> this blockquote. Unfortunately
> in some parsers, these are treated as the same blockquote.
"""

    def _find_blank_lines_between_blockquotes(self, document: Document) -> list[tuple[int, str]]:
        """Find blank lines that sit between two blockquote sections.

        Returns a list of (line_num, indent) tuples where line_num is the
        1-indexed blank line number and indent is the leading whitespace
        of the preceding blockquote line.
        """
        code_lines = document.code_block_lines
        total_lines = len(document.lines)
        results: list[tuple[int, str]] = []

        for line_num in range(1, total_lines + 1):
            if line_num in code_lines:
                continue

            line = document.get_line(line_num)
            if line is None or line.strip() != "":
                continue

            # Look backwards to find a blockquote line before this blank line
            has_blockquote_before = False
            before_indent = ""
            check_line = line_num - 1
            while check_line >= 1:
                if check_line in code_lines:
                    break
                prev_line = document.get_line(check_line)
                if prev_line is None:
                    break
                if prev_line.strip() == "":
                    check_line -= 1
                    continue
                stripped = prev_line.lstrip()
                if stripped.startswith(">"):
                    has_blockquote_before = True
                    before_indent = prev_line[: len(prev_line) - len(stripped)]
                break

            if not has_blockquote_before:
                continue

            # Look forwards to find a blockquote line after this blank line
            has_blockquote_after = False
            check_line = line_num + 1
            while check_line <= total_lines:
                if check_line in code_lines:
                    break
                next_line = document.get_line(check_line)
                if next_line is None:
                    break
                if next_line.strip() == "":
                    check_line += 1
                    continue
                if next_line.lstrip().startswith(">"):
                    has_blockquote_after = True
                break

            if has_blockquote_after:
                results.append((line_num, before_indent))

        return results

    def check(self, document: Document, config: MD028Config) -> list[Violation]:
        """Check for blank lines between blockquotes.

        The rule detects patterns like:
        > blockquote 1
        (blank line)
        > blockquote 2

        Where a blank line separates two blockquote sections.
        """
        violations: list[Violation] = []

        for line_num, _ in self._find_blank_lines_between_blockquotes(document):
            violations.append(
                Violation(
                    line=line_num,
                    column=1,
                    rule_id=self.id,
                    rule_name=self.name,
                    message="Blank line inside blockquote",
                    context=document.get_line(line_num),
                )
            )

        return violations

    def fix(self, document: Document, config: MD028Config) -> str | None:
        """Fix blank lines between blockquotes by adding > marker to continue the blockquote."""
        gaps = self._find_blank_lines_between_blockquotes(document)
        if not gaps:
            return None

        lines = document.content.split("\n")
        for line_num, indent in gaps:
            lines[line_num - 1] = indent + ">"

        return "\n".join(lines)
