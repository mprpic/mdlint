from dataclasses import dataclass, field
from typing import Literal

from markdown_it import MarkdownIt
from markdown_it.rules_inline import emphasis
from markdown_it.rules_inline.state_inline import StateInline
from markdown_it.token import Token

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation

_EMPHASIS_TYPES = ("em_open", "em_close", "strong_open", "strong_close")


def _record_delimiter_offsets(state: StateInline, silent: bool) -> bool:
    """Run markdown-it's emphasis tokenizer, tagging each delimiter with its source offset.

    Parsed em/strong tokens carry no position, and searching the text for their markup
    finds ``*`` and ``_`` in code spans, URLs and escapes too. The tokens a delimiter run
    produces are the ones later turned into em/strong tokens, so the tag survives.
    """
    start = state.pos
    if not emphasis.tokenize(state, silent):
        return False
    length = state.pos - start
    for offset, token in enumerate(state.tokens[len(state.tokens) - length :]):
        token.meta["delimiter_offset"] = start + offset
    return True


_OFFSET_PARSER = MarkdownIt()
_OFFSET_PARSER.inline.ruler.at("emphasis", _record_delimiter_offsets)


def emphasis_marker_positions(
    document: Document, token: Token, line_cursors: dict[int, int]
) -> dict[int, tuple[int, int]]:
    """Map the em/strong children of an inline token to the raw (line, column) of their markup.

    Shared by MD049 and MD050 so that fixes rewrite the markers themselves. The inline
    content is re-parsed with delimiter offsets recorded, and the offsets are trusted only
    when that parse yields the same em/strong sequence as the document and the raw line
    holds the expected markup at the computed column; anything else is left out.

    Each content line is located in its raw line after the container prefix. Table cells
    share a line, so ``line_cursors`` carries the search start from one cell to the next and
    must be shared across all inline tokens of a document, in order.
    """
    if not token.map:
        return {}

    # (offset of the line in the content, 1-indexed line, 0-indexed column or -1)
    content_lines: list[tuple[int, int, int]] = []
    offset = 0
    for index, content_line in enumerate(token.content.split("\n")):
        line_num = token.map[0] + 1 + index
        raw = document.get_line(line_num) or ""
        start = line_cursors.get(line_num, len(document.container_prefix(line_num)))
        column = raw.find(content_line, start)
        if column >= 0:
            line_cursors[line_num] = column + len(content_line)
        content_lines.append((offset, line_num, column))
        offset += len(content_line) + 1

    wanted = [
        (index, child)
        for index, child in enumerate(token.children or [])
        if child.type in _EMPHASIS_TYPES
    ]
    if not wanted:
        return {}
    reparsed = [
        child
        for child in _OFFSET_PARSER.parseInline(token.content)[0].children or []
        if child.type in _EMPHASIS_TYPES
    ]
    if [(c.type, c.markup) for c in reparsed] != [(c.type, c.markup) for _, c in wanted]:
        return {}

    positions: dict[int, tuple[int, int]] = {}
    for (index, child), parsed in zip(wanted, reparsed, strict=True):
        # A strong pair is tagged on its inner delimiter: the second "*" of an opener.
        marker_offset = parsed.meta["delimiter_offset"]
        if child.type == "strong_open":
            marker_offset -= 1
        line_offset, line_num, column = next(
            entry for entry in reversed(content_lines) if entry[0] <= marker_offset
        )
        if column < 0:
            continue
        column += marker_offset - line_offset
        raw = document.get_line(line_num) or ""
        if raw[column : column + len(child.markup)] == child.markup:
            positions[index] = (line_num, column + 1)
    return positions


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
        line_cursors: dict[int, int] = {}

        for token in document.tokens:
            if token.type != "inline" or not token.children or not token.map:
                continue

            positions = emphasis_marker_positions(document, token, line_cursors)

            for i, child in enumerate(token.children):
                if child.type != "em_open":
                    continue

                marker = child.markup
                if marker not in self.MARKER_TO_STYLE:
                    continue

                line, column = positions.get(i, (token.map[0] + 1, 1))

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
        line_cursors: dict[int, int] = {}

        for token in document.tokens:
            if token.type != "inline" or not token.children or not token.map:
                continue

            positions = emphasis_marker_positions(document, token, line_cursors)
            # Opener position of each open em if it should be fixed, None otherwise
            fix_stack: list[tuple[int, int] | None] = []

            for i, child in enumerate(token.children):
                if child.type == "em_open":
                    marker = child.markup
                    if marker not in self.MARKER_TO_STYLE:
                        continue

                    position = positions.get(i)
                    current_style = self.MARKER_TO_STYLE[marker]
                    should_fix = (
                        position is not None
                        and current_style != expected_style
                        and position[0] not in code_block_lines
                        and not (
                            expected_style == "underscore"
                            and self._is_intraword_emphasis(token.children, i)
                        )
                    )
                    fix_stack.append(position if should_fix else None)
                    continue

                if child.type == "em_close":
                    marker = child.markup
                    if marker not in self.MARKER_TO_STYLE:
                        continue

                    open_position = fix_stack.pop() if fix_stack else None
                    close_position = positions.get(i)
                    # Rewrite both markers or neither, so a pair is never left mismatched
                    if open_position is not None and close_position is not None:
                        replacements.extend((open_position, close_position))
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
