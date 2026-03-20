from dataclasses import dataclass

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD038Config(RuleConfig):
    """Configuration for MD038 rule."""


class MD038(Rule[MD038Config]):
    """Spaces inside code span elements."""

    id = "MD038"
    name = "no-space-in-code"
    summary = "Spaces inside code span elements"
    config_class = MD038Config

    description = (
        "This rule is triggered when inline code spans have unnecessary spaces "
        "adjacent to the backticks. For example: `` `  some code  ` `` "
        "instead of `` `some code` ``. Per the CommonMark specification, symmetric "
        "single-space padding (e.g., `` ` code ` ``) is valid because the parser "
        "strips one space from each side, so it is not flagged by this rule."
    )

    rationale = (
        "Spaces inside code spans are usually unintentional and can lead to "
        "inconsistent formatting. The extra whitespace adds no value and may "
        "cause confusion about where the code actually starts or ends."
    )

    example_valid = """\
# Valid Code Spans

This document has `properly formatted` code spans.

Multiple code spans: `one` and `two` and `three`.

Code span with backticks inside: `` `backticks` ``.

Symmetric space padding: ` code ` is valid per CommonMark.
"""

    example_invalid = """\
# Invalid Code Spans

This has ` leading space` in code.

This has `trailing space ` in code.

This has `  spaces on both sides  ` in code.
"""

    def check(self, document: Document, config: MD038Config) -> list[Violation]:
        """Check for spaces inside code span elements."""
        violations: list[Violation] = []

        for token in document.tokens:
            if token.type != "inline" or not token.children or not token.map:
                continue

            start_line_1 = token.map[0] + 1
            end_line_1 = token.map[1]
            source_lines = [
                document.get_line(ln) or "" for ln in range(start_line_1, end_line_1 + 1)
            ]
            source = "\n".join(source_lines)

            search_pos = 0
            for child in token.children:
                if child.type != "code_inline":
                    continue

                markup = child.markup
                mlen = len(markup)

                open_idx = _find_backtick_string(source, markup, search_pos)
                if open_idx is None:
                    continue

                content_start = open_idx + mlen
                close_idx = _find_backtick_string(source, markup, content_start)
                if close_idx is None:
                    continue

                raw_content = source[content_start:close_idx]
                search_pos = close_idx + mlen

                # Skip if content is only whitespace (valid per CommonMark spec)
                if not raw_content.strip():
                    continue

                # Per CommonMark spec §6.1: if content both begins AND ends with
                # a space character, one space is stripped from each side by the
                # parser. Emulate this to check the effective rendered content.
                if raw_content.startswith(" ") and raw_content.endswith(" "):
                    effective = raw_content[1:-1]
                    padding_offset = 1
                else:
                    effective = raw_content
                    padding_offset = 0

                has_leading = effective.startswith((" ", "\t"))
                has_trailing = effective.endswith((" ", "\t"))

                if has_leading:
                    char_offset = content_start + padding_offset
                    line_num, column = _offset_to_position(source_lines, char_offset, start_line_1)
                    violations.append(
                        Violation(
                            line=line_num,
                            column=column,
                            rule_id=self.id,
                            rule_name=self.name,
                            message="Code span has leading space(s)",
                            context=document.get_line(line_num),
                        )
                    )

                if has_trailing:
                    trailing_spaces = len(effective) - len(effective.rstrip())
                    char_offset = content_start + padding_offset + len(effective) - trailing_spaces
                    line_num, column = _offset_to_position(source_lines, char_offset, start_line_1)
                    violations.append(
                        Violation(
                            line=line_num,
                            column=column,
                            rule_id=self.id,
                            rule_name=self.name,
                            message="Code span has trailing space(s)",
                            context=document.get_line(line_num),
                        )
                    )

        return violations

    def fix(self, document: Document, config: MD038Config) -> str | None:
        """Fix spaces inside code span elements by stripping unnecessary whitespace."""
        lines = document.content.split("\n")
        changed = False

        for token in document.tokens:
            if token.type != "inline" or not token.children or not token.map:
                continue

            start_line_0 = token.map[0]
            end_line_0 = token.map[1] - 1
            source_lines = lines[start_line_0 : end_line_0 + 1]
            source = "\n".join(source_lines)

            new_source = source
            offset_adj = 0

            search_pos = 0
            for child in token.children:
                if child.type != "code_inline":
                    continue

                markup = child.markup
                mlen = len(markup)

                open_idx = _find_backtick_string(source, markup, search_pos)
                if open_idx is None:
                    continue

                content_start = open_idx + mlen
                close_idx = _find_backtick_string(source, markup, content_start)
                if close_idx is None:
                    continue

                raw_content = source[content_start:close_idx]
                search_pos = close_idx + mlen

                if not raw_content.strip():
                    continue

                if raw_content.startswith(" ") and raw_content.endswith(" "):
                    effective = raw_content[1:-1]
                    had_padding = True
                else:
                    effective = raw_content
                    had_padding = False

                has_leading = effective.startswith((" ", "\t"))
                has_trailing = effective.endswith((" ", "\t"))

                if not has_leading and not has_trailing:
                    continue

                stripped = effective.strip()
                if had_padding:
                    new_span = f"{markup} {stripped} {markup}"
                else:
                    new_span = f"{markup}{stripped}{markup}"

                old_span_len = close_idx + mlen - open_idx
                adj_start = open_idx + offset_adj
                adj_end = adj_start + old_span_len
                new_source = new_source[:adj_start] + new_span + new_source[adj_end:]
                offset_adj += len(new_span) - old_span_len
                changed = True

            if new_source != source:
                new_lines = new_source.split("\n")
                lines[start_line_0 : end_line_0 + 1] = new_lines

        if not changed:
            return None
        return "\n".join(lines)


def _find_backtick_string(source: str, markup: str, start: int) -> int | None:
    """Find the next occurrence of a backtick string that is not part of a longer run.

    Per CommonMark spec, a backtick string is a string of one or more backtick
    characters that is neither preceded nor followed by a backtick character.
    """
    mlen = len(markup)
    pos = start
    while pos <= len(source) - mlen:
        idx = source.find(markup, pos)
        if idx < 0:
            return None
        # Must not be preceded by a backtick
        if idx > 0 and source[idx - 1] == "`":
            pos = idx + 1
            continue
        # Must not be followed by a backtick
        end = idx + mlen
        if end < len(source) and source[end] == "`":
            pos = idx + 1
            continue
        return idx
    return None


def _offset_to_position(source_lines: list[str], offset: int, start_line_1: int) -> tuple[int, int]:
    """Convert a character offset in joined source to (line_number, column)."""
    current_offset = 0
    for i, line in enumerate(source_lines):
        line_end = current_offset + len(line)
        if offset <= line_end:
            column = offset - current_offset + 1
            return start_line_1 + i, column
        current_offset = line_end + 1  # +1 for newline
    return start_line_1 + len(source_lines) - 1, 1
