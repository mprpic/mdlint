import re
from dataclasses import dataclass, field

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD013Config(RuleConfig):
    """Configuration for MD013 rule."""

    line_length: int = field(
        default=80,
        metadata={
            "description": "Maximum allowed line length. Set to 0 to disable.",
        },
    )
    heading_line_length: int = field(
        default=80,
        metadata={
            "description": "Maximum line length for headings. Set to 0 to disable.",
        },
    )
    code_block_line_length: int = field(
        default=80,
        metadata={
            "description": "Maximum line length for code blocks. Set to 0 to disable.",
        },
    )
    code_blocks: bool = field(
        default=True,
        metadata={
            "description": "Include code blocks in the check.",
        },
    )
    tables: bool = field(
        default=True,
        metadata={
            "description": "Include tables in the check.",
        },
    )
    headings: bool = field(
        default=True,
        metadata={
            "description": "Include headings in the check.",
        },
    )
    strict: bool = field(
        default=False,
        metadata={
            "description": "Strict mode - flag all lines exceeding limit.",
        },
    )


class MD013(Rule[MD013Config]):
    """Line length."""

    id = "MD013"
    name = "line-length"
    summary = "Line length"
    config_class = MD013Config

    description = (
        "This rule detects lines that exceed the configured maximum length "
        "(default: 80 characters). Separate limits can be set for headings "
        "(`heading_line_length`) and code blocks (`code_block_line_length`). "
        "By default, lines are allowed to exceed the limit if the only content "
        "pushing the line over is a trailing unbreakable token (e.g. a long "
        "URL). Set `strict` to `true` to flag all lines exceeding the limit. "
        "Lines containing only links/images and reference definitions are "
        "always exempt."
    )

    rationale = (
        "Extremely long lines can be difficult to work with in some editors "
        "and can reduce readability. Wrapping lines at a reasonable length "
        "improves the editing experience and makes diffs easier to review."
    )

    example_valid = """\
# Valid Line Length

This is a short line that is within the limit.

Here is another paragraph with lines that are well under the eighty character
limit that is configured by default.

- List items should also be short
- Like these ones here
"""

    example_invalid = """\
# Invalid Line Length

This line is way too long and exceeds the default eighty character limit for this rule.

Another paragraph with a line that is also way too long and should be flagged by the linter.
"""

    def check(self, document: Document, config: MD013Config) -> list[Violation]:
        """Check for line length violations."""
        violations: list[Violation] = []

        # Build sets of line numbers for different content types
        heading_lines = self._get_heading_lines(document)
        code_block_lines = document.code_block_lines
        table_lines = self._get_table_lines(document)
        ref_def_lines = self._get_reference_definition_lines(document)
        link_only_lines = self._get_link_only_lines(document)

        for line_num, line in enumerate(document.lines, start=1):
            line_length = len(line)

            # Reference definitions are always exempt (even in strict mode)
            if line_num in ref_def_lines:
                continue

            # Determine the applicable max length based on content type
            if line_num in code_block_lines:
                if not config.code_blocks:
                    continue
                max_length = config.code_block_line_length
            elif line_num in heading_lines:
                if not config.headings:
                    continue
                max_length = config.heading_line_length
            elif line_num in table_lines:
                if not config.tables:
                    continue
                max_length = config.line_length
            else:
                max_length = config.line_length

            if max_length <= 0:
                continue

            if line_length <= max_length:
                continue

            if not config.strict:
                # In non-strict mode, allow lines where only the trailing
                # unbreakable token pushes the line over the limit
                if self._is_not_wrappable(line, max_length):
                    continue

                # Exempt lines that contain only links/images
                if line_num in link_only_lines:
                    continue

            violations.append(
                Violation(
                    line=line_num,
                    column=max_length + 1,
                    rule_id=self.id,
                    rule_name=self.name,
                    message=f"Expected max {max_length} characters, found {line_length}",
                    context=line,
                )
            )

        return violations

    @staticmethod
    def _get_heading_lines(document: Document) -> set[int]:
        """Get line numbers that are part of headings."""
        heading_lines: set[int] = set()

        for token in document.tokens:
            if token.type == "heading_open" and token.map:
                start_line = token.map[0] + 1
                end_line = token.map[1]
                for line_num in range(start_line, end_line + 1):
                    heading_lines.add(line_num)

        return heading_lines

    @staticmethod
    def _get_table_lines(document: Document) -> set[int]:
        """Get line numbers that are part of tables."""
        table_lines: set[int] = set()

        for token in document.tokens:
            if token.type == "table_open" and token.map:
                start_line = token.map[0] + 1
                end_line = token.map[1]
                for line_num in range(start_line, end_line + 1):
                    table_lines.add(line_num)

        return table_lines

    @staticmethod
    def _get_reference_definition_lines(document: Document) -> set[int]:
        """Get line numbers that are reference definitions."""
        ref_lines: set[int] = set()

        for line_num, line in enumerate(document.lines, start=1):
            if Rule.REFERENCE_DEF_PATTERN.match(line):
                ref_lines.add(line_num)

        return ref_lines

    @staticmethod
    def _get_link_only_lines(document: Document) -> set[int]:
        """Get line numbers where all content is links or images.

        A line is "link-only" if the paragraph content on that line consists
        entirely of links/images (possibly wrapped in emphasis). These lines
        cannot be split without breaking the URL.
        """
        link_only_lines: set[int] = set()

        for i, token in enumerate(document.tokens):
            if token.type != "paragraph_open" or not token.map:
                continue

            if i + 1 >= len(document.tokens):
                continue
            inline_token = document.tokens[i + 1]
            if inline_token.type != "inline" or not inline_token.children:
                continue

            start_line = token.map[0] + 1

            # Split children by line breaks into per-line groups
            line_groups: list[list] = [[]]
            for child in inline_token.children:
                if child.type in ("softbreak", "hardbreak"):
                    line_groups.append([])
                else:
                    line_groups[-1].append(child)

            for offset, group in enumerate(line_groups):
                if MD013._is_link_only_group(group):
                    link_only_lines.add(start_line + offset)

        return link_only_lines

    @staticmethod
    def _is_link_only_group(children: list) -> bool:
        """Check if a group of inline tokens contains only links/images."""
        has_link = False
        in_link = 0

        for child in children:
            if child.type == "link_open":
                in_link += 1
                has_link = True
            elif child.type == "link_close":
                in_link -= 1
            elif child.type == "image":
                has_link = True
            elif child.type in (
                "strong_open",
                "strong_close",
                "em_open",
                "em_close",
            ):
                pass
            elif child.type == "text" and in_link == 0:
                if child.content.strip():
                    return False
            elif in_link == 0:
                return False

        return has_link

    @staticmethod
    def _is_not_wrappable(line: str, max_length: int) -> bool:
        """Check if a line cannot be wrapped.

        A line is not wrappable if removing the trailing unbreakable token
        (the last run of non-whitespace characters) brings the line within
        the limit. This allows long URLs and other unbreakable content to
        exceed the limit when they are the only reason the line is too long.
        """
        effective_line = re.sub(r"\S+$", "#", line)
        return len(effective_line) <= max_length
