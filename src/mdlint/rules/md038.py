import re
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

    # Pattern to find code spans: backticks followed by content and closing backticks
    # Captures: (opening backticks)(content)(closing backticks)
    CODE_SPAN_PATTERN = re.compile(r"(`+)(.+?)\1")

    def check(self, document: Document, config: MD038Config) -> list[Violation]:
        """Check for spaces inside code span elements."""
        violations: list[Violation] = []

        # Build set of line numbers inside code blocks
        code_block_lines = document.code_block_lines

        for line_num, line in enumerate(document.lines, start=1):
            # Skip lines in code blocks
            if line_num in code_block_lines:
                continue

            # Find all code spans on this line
            for match in self.CODE_SPAN_PATTERN.finditer(line):
                opening_backticks = match.group(1)
                content = match.group(2)
                span_start = match.start()

                # Skip if content is only whitespace (valid per CommonMark spec)
                if content.strip() == "":
                    continue

                # Per CommonMark spec §6.1: if content both begins AND ends with
                # a space character, one space is stripped from each side by the
                # parser. Emulate this to check the effective rendered content.
                if content.startswith(" ") and content.endswith(" "):
                    effective = content[1:-1]
                    padding_offset = 1
                else:
                    effective = content
                    padding_offset = 0

                has_leading_space = effective.startswith((" ", "\t"))
                has_trailing_space = effective.endswith((" ", "\t"))

                if has_leading_space:
                    column = span_start + len(opening_backticks) + padding_offset + 1
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

                if has_trailing_space:
                    trailing_spaces = len(effective) - len(effective.rstrip())
                    effective_start = span_start + len(opening_backticks) + padding_offset
                    column = effective_start + len(effective) - trailing_spaces + 1
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
        code_block_lines = document.code_block_lines
        changed = False
        lines = document.content.split("\n")

        for line_idx, line in enumerate(lines):
            line_num = line_idx + 1
            if line_num in code_block_lines:
                continue

            new_line = self.CODE_SPAN_PATTERN.sub(lambda m: self._fix_code_span(m), line)
            if new_line != line:
                lines[line_idx] = new_line
                changed = True

        if not changed:
            return None
        return "\n".join(lines)

    @staticmethod
    def _fix_code_span(match: re.Match) -> str:
        """Fix a single code span match by removing unnecessary spaces."""
        backticks = match.group(1)
        content = match.group(2)

        # Skip if content is only whitespace (valid per CommonMark spec)
        if content.strip() == "":
            return match.group(0)

        # Determine the effective content the same way the check does
        if content.startswith(" ") and content.endswith(" "):
            effective = content[1:-1]
            had_padding = True
        else:
            effective = content
            had_padding = False

        has_leading = effective.startswith((" ", "\t"))
        has_trailing = effective.endswith((" ", "\t"))

        # No violation — return unchanged
        if not has_leading and not has_trailing:
            return match.group(0)

        stripped = effective.strip()

        # Re-add symmetric padding if it was present originally
        if had_padding:
            return f"{backticks} {stripped} {backticks}"
        return f"{backticks}{stripped}{backticks}"
