from dataclasses import dataclass, field

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD010Config(RuleConfig):
    """Configuration for MD010 rule."""

    code_blocks: bool = field(
        default=True,
        metadata={
            "description": (
                "Whether to check code blocks and inline code spans for hard tabs. "
                "When True (default), code blocks and inline code spans are checked. "
                "When False, fenced code blocks, indented code blocks, and inline "
                "code spans are ignored."
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
        "triggers on any lines that contain tab characters."
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

        results: list[tuple[int, list[int]]] = []
        for line_num, line in enumerate(document.lines, start=1):
            if line_num in code_block_lines:
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
        """Fix hard tabs by replacing them with spaces."""
        tab_positions = self._get_tab_positions(document, config)
        if not tab_positions:
            return None

        tab_columns_by_line = {line_num: set(columns) for line_num, columns in tab_positions}
        lines = document.content.split("\n")
        for line_num, tab_columns in tab_columns_by_line.items():
            line = lines[line_num - 1]
            new_line = []
            column = 0
            for char in line:
                column += 1
                if char == "\t" and column in tab_columns:
                    new_line.append("    ")
                else:
                    new_line.append(char)
            lines[line_num - 1] = "".join(new_line)

        return "\n".join(lines)
