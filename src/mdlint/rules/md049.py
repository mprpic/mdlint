from dataclasses import dataclass, field
from typing import Literal

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD049Config(RuleConfig):
    """Configuration for MD049 rule."""

    EmphasisStyle = Literal["asterisk", "consistent", "underscore"]

    style: EmphasisStyle = field(
        default="consistent",
        metadata={
            "description": "Required emphasis style.",
            "option_descriptions": {
                "consistent": "All emphasis markers must match the first one used",
                "asterisk": "All emphasis markers must be `*`",
                "underscore": "All emphasis markers must be `_`",
            },
        },
    )


class MD049(Rule[MD049Config]):
    """Emphasis style should be consistent."""

    id = "MD049"
    name = "emphasis-style"
    summary = "Emphasis style should be consistent"
    config_class = MD049Config

    description = (
        "This rule ensures that emphasis markers (for italic text) throughout "
        "a document follow a consistent style. It validates that emphasis uses "
        "matching symbols (asterisks or underscores) according to the configured "
        "preference."
    )

    rationale = (
        "Consistent formatting makes it easier to understand a document. "
        "Uniform emphasis styling promotes readability."
    )

    example_valid = """\
# Consistent Emphasis Style

This text has *italic* words using asterisks.

Here is *more italic* text that is consistent.

Multiple *words* in *a* sentence are *fine*.
"""

    example_invalid = """\
# Inconsistent Emphasis Style

This text has *italic* with asterisks.

But this uses _italic_ with underscores.
"""

    MARKER_TO_STYLE = {
        "*": "asterisk",
        "_": "underscore",
    }

    def check(self, document: Document, config: MD049Config) -> list[Violation]:
        """Check for emphasis style consistency."""
        violations: list[Violation] = []

        expected_style: str | None = None
        if config.style in ("asterisk", "underscore"):
            expected_style = config.style

        code_block_lines = document.code_block_lines

        for token in document.tokens:
            if token.type != "inline" or not token.children or not token.map:
                continue

            base_line = token.map[0] + 1
            search_pos = 0

            for i, child in enumerate(token.children):
                # Advance past marker tokens to keep search_pos correct
                if child.type in ("em_close", "strong_open", "strong_close") and child.markup:
                    pos = token.content.find(child.markup, search_pos)
                    if pos >= 0:
                        search_pos = pos + len(child.markup)
                    continue

                if child.type != "em_open":
                    continue

                marker = child.markup
                if marker not in self.MARKER_TO_STYLE:
                    continue

                line, column, search_pos = self._find_marker_position(
                    token.content, marker, search_pos, base_line
                )

                if line in code_block_lines:
                    continue

                current_style = self.MARKER_TO_STYLE[marker]

                if expected_style is None:
                    expected_style = current_style
                elif current_style != expected_style:
                    # Intraword emphasis can only use asterisks per
                    # CommonMark spec, so don't flag it when expecting
                    # underscores.
                    if expected_style == "underscore" and self._is_intraword_emphasis(
                        token.children, i
                    ):
                        continue

                    violations.append(
                        Violation(
                            line=line,
                            column=column,
                            rule_id=self.id,
                            rule_name=self.name,
                            message=(
                                f"Emphasis style: expected {expected_style}, found {current_style}"
                            ),
                            context=document.get_line(line),
                        )
                    )

        return violations

    @staticmethod
    def _find_marker_position(
        content: str, marker: str, search_pos: int, base_line: int
    ) -> tuple[int, int, int]:
        """Find line and column of a marker in raw inline content."""
        pos = content.find(marker, search_pos)
        if pos < 0:
            return base_line, 1, search_pos

        text_before = content[:pos]
        line_offset = text_before.count("\n")
        last_nl = text_before.rfind("\n")
        column = pos - last_nl  # 1-indexed (rfind returns -1 when no \n)

        return base_line + line_offset, column, pos + len(marker)

    @staticmethod
    def _is_intraword_emphasis(children: list, em_open_index: int) -> bool:
        """Check if emphasis is intraword (underscores can't replace it)."""
        # Check if preceded by alphanumeric character
        if em_open_index > 0:
            prev = children[em_open_index - 1]
            if prev.type == "text" and prev.content and prev.content[-1].isalnum():
                return True

        # Find matching em_close and check if followed by alphanumeric
        depth = 0
        for j in range(em_open_index, len(children)):
            if children[j].type == "em_open":
                depth += 1
            elif children[j].type == "em_close":
                depth -= 1
                if depth == 0:
                    if j + 1 < len(children):
                        next_token = children[j + 1]
                        if (
                            next_token.type == "text"
                            and next_token.content
                            and next_token.content[0].isalnum()
                        ):
                            return True
                    break

        return False

    def fix(self, document: Document, config: MD049Config) -> str | None:
        """Fix emphasis style by replacing markers to match expected style."""
        expected_style: str | None = None
        if config.style in ("asterisk", "underscore"):
            expected_style = config.style

        code_block_lines = document.code_block_lines

        # For "consistent" mode, determine style from first emphasis marker
        if expected_style is None:
            for token in document.tokens:
                if token.type != "inline" or not token.children:
                    continue
                for child in token.children:
                    if child.type == "em_open" and child.markup in self.MARKER_TO_STYLE:
                        expected_style = self.MARKER_TO_STYLE[child.markup]
                        break
                if expected_style:
                    break

        if expected_style is None:
            return None

        target_marker = "*" if expected_style == "asterisk" else "_"

        # Collect (line_1indexed, column_1indexed) positions to replace
        replacements: list[tuple[int, int]] = []

        for token in document.tokens:
            if token.type != "inline" or not token.children or not token.map:
                continue

            base_line = token.map[0] + 1
            search_pos = 0
            # Track whether each em_open should be fixed; pop on em_close
            fix_stack: list[bool] = []

            for i, child in enumerate(token.children):
                if child.type in ("strong_open", "strong_close") and child.markup:
                    pos = token.content.find(child.markup, search_pos)
                    if pos >= 0:
                        search_pos = pos + len(child.markup)
                    continue

                if child.type == "em_open":
                    marker = child.markup
                    if marker not in self.MARKER_TO_STYLE:
                        continue

                    line, column, search_pos = self._find_marker_position(
                        token.content, marker, search_pos, base_line
                    )

                    current_style = self.MARKER_TO_STYLE[marker]
                    should_fix = (
                        current_style != expected_style
                        and line not in code_block_lines
                        and not (
                            expected_style == "underscore"
                            and self._is_intraword_emphasis(token.children, i)
                        )
                    )
                    fix_stack.append(should_fix)

                    if should_fix:
                        replacements.append((line, column))
                    continue

                if child.type == "em_close":
                    marker = child.markup
                    if marker not in self.MARKER_TO_STYLE:
                        continue

                    line, column, search_pos = self._find_marker_position(
                        token.content, marker, search_pos, base_line
                    )

                    should_fix = fix_stack.pop() if fix_stack else False
                    if should_fix:
                        replacements.append((line, column))
                    continue

        if not replacements:
            return None

        lines = document.content.split("\n")
        for line_num, column in sorted(replacements, reverse=True):
            line_idx = line_num - 1
            col_idx = column - 1
            line = lines[line_idx]
            lines[line_idx] = line[:col_idx] + target_marker + line[col_idx + 1 :]

        return "\n".join(lines)
