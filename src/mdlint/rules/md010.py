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

    def check(self, document: Document, config: MD010Config) -> list[Violation]:
        """Check for hard tab characters."""
        violations: list[Violation] = []

        # Build sets of lines/columns to skip when code is excluded
        code_block_lines: set[int] = set()
        code_span_positions: dict[int, set[int]] = {}
        if not config.code_blocks:
            code_block_lines = self._get_code_block_lines(document)
            code_span_positions = self._get_code_span_positions(document)

        # Check each line for tab characters
        for line_num, line in enumerate(document.lines, start=1):
            # Skip lines in code blocks if configured to ignore them
            if line_num in code_block_lines:
                continue

            skip_columns = code_span_positions.get(line_num, set())

            # Find all tab characters in the line
            column = 0
            for char in line:
                column += 1
                if char == "\t" and column not in skip_columns:
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
