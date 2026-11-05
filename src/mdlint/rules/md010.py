from dataclasses import dataclass, field

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation

# CommonMark expands tabs to multiples of 4 columns when measuring indentation
_TAB_SIZE = 4


@dataclass
class MD010Config(RuleConfig):
    """Configuration for MD010 rule."""

    code_blocks: bool = field(
        default=False,
        metadata={
            "description": (
                "Whether to check code blocks and inline code spans for hard tabs. "
                "When False (default), fenced code blocks, indented code blocks, and "
                "inline code spans are ignored, since some languages (such as "
                "Makefiles) require tabs. When True, they are checked and fixed."
            ),
        },
    )


class MD010(Rule[MD010Config]):
    """No hard tabs."""

    id = "MD010"
    name = "no-hard-tabs"
    summary = "No hard tabs"
    config_class = MD010Config

    description = (
        "This rule detects hard tab characters in Markdown files. It "
        "triggers on any lines that contain tab characters. Code blocks and "
        "inline code spans are skipped unless `code_blocks` is enabled, and "
        "front matter is never checked. The fix expands each tab to the next "
        "4-column tab stop, so content stays on the same column, and removes "
        "trailing whitespace that contains a tab instead of turning it into "
        "spaces, which would create a hard line break."
    )

    rationale = (
        "Hard tabs are often rendered inconsistently by different editors "
        "and can be harder to work with than spaces. Different applications "
        "interpret tab width differently (some use 4 spaces, others 8), "
        "creating formatting problems across platforms."
    )

    def _get_tab_positions(
        self, document: Document, config: MD010Config
    ) -> list[tuple[int, list[int]]]:
        """Return list of (line_num, tab_columns) for lines with violating tabs."""
        code_block_lines: set[int] = set()
        code_span_positions: dict[int, set[int]] = {}
        if not config.code_blocks:
            code_block_lines = document.code_block_lines
            code_span_positions = document.code_span_positions
        front_matter_lines = document.front_matter_lines

        results: list[tuple[int, list[int]]] = []
        for line_num, line in enumerate(document.lines, start=1):
            if line_num in code_block_lines or line_num in front_matter_lines:
                continue

            if "\t" not in line:
                continue

            skip_columns = code_span_positions.get(line_num, set())

            columns: list[int] = []
            column = 0
            for char in line:
                column += 1
                if char == "\t" and column not in skip_columns:
                    columns.append(column)

            if columns:
                results.append((line_num, columns))

        return results

    def check(self, document: Document, config: MD010Config) -> list[Violation]:
        """Check for hard tab characters."""
        violations: list[Violation] = []

        for line_num, columns in self._get_tab_positions(document, config):
            for column in columns:
                violations.append(
                    Violation(
                        line=line_num,
                        column=column,
                        rule_id=self.id,
                        rule_name=self.name,
                        message="Hard tab character found",
                        context=document.get_line(line_num),
                    )
                )

        return violations

    def fix(self, document: Document, config: MD010Config) -> str | None:
        """Fix hard tabs by expanding them to spaces.

        Tabs are padded to the next tab stop rather than replaced by a fixed number of
        spaces, so text after a tab (such as list item content) keeps its column and its
        Markdown meaning. Tabs left alone (in code spans) still occupy their original
        width, so later tabs on the line are measured against the original layout.
        """
        tab_positions = self._get_tab_positions(document, config)
        if not tab_positions:
            return None

        lines = document.content.split("\n")
        for line_num, columns in tab_positions:
            tab_columns = set(columns)
            line = lines[line_num - 1]
            body = line.rstrip(" \t")
            if max(tab_columns) > len(body):
                # Expanded trailing tabs would become trailing spaces, i.e. a hard break, so
                # they are dropped. Two or more spaces after the last tab already form one,
                # and are kept.
                trailing = line[len(body) :]
                spaces = trailing[trailing.rfind("\t") + 1 :]
                line = body + (spaces if len(spaces) >= 2 else "")
            new_line: list[str] = []
            width = 0
            for column, char in enumerate(line, start=1):
                if char == "\t":
                    tab_stop = width + _TAB_SIZE - width % _TAB_SIZE
                    new_line.append(" " * (tab_stop - width) if column in tab_columns else char)
                    width = tab_stop
                else:
                    new_line.append(char)
                    width += 1
            lines[line_num - 1] = "".join(new_line)

        return "\n".join(lines)
