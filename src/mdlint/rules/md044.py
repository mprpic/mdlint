import re
from collections.abc import Iterator
from dataclasses import dataclass, field

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD044Config(RuleConfig):
    """Configuration for MD044 rule."""

    names: list[str] = field(
        default_factory=list,
        metadata={"description": "List of proper names with correct capitalization."},
    )
    code_blocks: bool = field(
        default=True,
        metadata={"description": "Whether to check inside code blocks and inline code."},
    )
    html_elements: bool = field(
        default=True,
        metadata={"description": "Whether to check inside HTML elements."},
    )


class MD044(Rule[MD044Config]):
    """Proper names should have correct capitalization."""

    id = "MD044"
    name = "proper-names"
    summary = "Proper names should have correct capitalization"
    config_class = MD044Config

    description = (
        "This rule checks that proper names (like product or project names) "
        "are capitalized consistently throughout the document. The expected "
        "capitalization is specified in the `names` configuration option. For example:\n\n"
        "```\n"
        'names = ["JavaScript", "Github", "Python"]\n'
        "```"
    )

    rationale = (
        "Inconsistent capitalization of proper names looks unprofessional and "
        "can confuse readers. Using the correct capitalization shows attention "
        "to detail and respect for the named entity."
    )

    example_valid = """\
# Valid Document

This document uses JavaScript correctly.

We also use GitHub and Python with proper capitalization.

- JavaScript is great
- GitHub is useful
- Python is powerful
"""

    example_invalid = """\
# Invalid Document

This document uses javascript incorrectly.

We also use github and python with improper capitalization.

- javascript is great
- github is useful
- python is powerful
"""

    def _find_name_mismatches(
        self, document: Document, config: MD044Config
    ) -> Iterator[tuple[int, int, str, str]]:
        """Yield name capitalization mismatches.

        Yields tuples of (line_num, column, expected_name, found_name) where
        column is 1-indexed.
        """
        if not config.names:
            return

        # Sort names by length (longest first) to match longer names before shorter ones
        names = sorted(config.names, key=lambda x: (-len(x), x))
        names_set = set(config.names)

        # Pre-compile regex patterns for each name
        name_patterns: list[tuple[str, re.Pattern[str]]] = []
        for name in names:
            escaped_name = re.escape(name)
            start = r"\b_*" if re.match(r"^\w", name) else ""
            end = r"_*\b" if re.match(r".*\w$", name) else ""
            pattern = f"({start})({escaped_name})({end})"
            name_patterns.append((name, re.compile(pattern, re.IGNORECASE)))

        # Use AST to determine which lines to scan and what to exclude.
        # Lines not in scannable_lines are automatically skipped — this handles
        # front matter, fence markers (info strings), and reference definitions.
        scannable_lines: set[int] = set()
        exclusion_ranges: dict[int, list[tuple[int, int]]] = {}

        for token in document.tokens:
            if not token.map or token.type == "front_matter":
                continue

            if token.type == "fence":
                if config.code_blocks:
                    # Content lines only (skip opening/closing fence markers)
                    for ln in range(token.map[0] + 2, token.map[1]):
                        scannable_lines.add(ln)
                continue

            if token.type == "code_block":
                if config.code_blocks:
                    for ln in range(token.map[0] + 1, token.map[1] + 1):
                        scannable_lines.add(ln)
                continue

            if token.type == "html_block":
                if config.html_elements:
                    for ln in range(token.map[0] + 1, token.map[1] + 1):
                        scannable_lines.add(ln)
                continue

            if token.type != "inline" or not token.children:
                continue

            for ln in range(token.map[0] + 1, token.map[1] + 1):
                scannable_lines.add(ln)

            # Detect autolinks and link URLs to exclude from scanning
            current_line = token.map[0] + 1
            for child in token.children:
                if child.type in ("softbreak", "hardbreak"):
                    current_line += 1
                elif child.type == "link_open":
                    href = child.attrs.get("href", "")
                    if not href:
                        continue
                    source = document.get_line(current_line) or ""
                    if child.markup == "autolink":
                        # Autolink: <URL>
                        target = f"<{href}>"
                    else:
                        # Regular/image link: ](URL...) — exclude URL portion
                        target = f"]({href}"
                    idx = source.find(target)
                    if idx >= 0:
                        # Find the closing delimiter to get full exclusion range
                        close_char = ">" if child.markup == "autolink" else ")"
                        close_idx = source.find(close_char, idx + len(target))
                        end = (close_idx + 2) if close_idx >= 0 else (idx + len(target) + 1)
                        exclusion_ranges.setdefault(current_line, []).append((idx + 1, end))

        # Build inline code exclusion when code_blocks is disabled
        code_span_positions: dict[int, set[int]] = {}
        if not config.code_blocks:
            code_span_positions = document.code_span_positions

        # Scan each scannable line for name violations
        matched_ranges: dict[int, list[tuple[int, int]]] = {}

        for line_num in sorted(scannable_lines):
            line = document.get_line(line_num)
            if not line:
                continue

            exclusions = exclusion_ranges.get(line_num, [])
            line_code_cols = code_span_positions.get(line_num, set())
            line_matched = matched_ranges.setdefault(line_num, [])

            for name, name_re in name_patterns:
                for match in name_re.finditer(line):
                    matched_name = match.group(2)
                    column = match.start(2) + 1

                    if matched_name in names_set:
                        line_matched.append((column, column + len(matched_name)))
                        continue

                    if self._overlaps_ranges(column, column + len(matched_name), line_matched):
                        continue

                    if self._in_exclusion_range(column, exclusions):
                        continue

                    if not config.code_blocks and column in line_code_cols:
                        continue

                    yield line_num, column, name, matched_name
                    line_matched.append((column, column + len(matched_name)))

    def check(self, document: Document, config: MD044Config) -> list[Violation]:
        """Check for proper-names violations."""
        return [
            Violation(
                line=line_num,
                column=column,
                rule_id=self.id,
                rule_name=self.name,
                message=f"Expected '{expected}' but found '{found}'",
                context=document.get_line(line_num),
            )
            for line_num, column, expected, found in self._find_name_mismatches(document, config)
        ]

    def fix(self, document: Document, config: MD044Config) -> str | None:
        """Fix proper-name capitalization violations."""
        matches_by_line: dict[int, list[tuple[int, str, str]]] = {}
        for line_num, column, expected, found in self._find_name_mismatches(document, config):
            matches_by_line.setdefault(line_num, []).append((column, expected, found))

        if not matches_by_line:
            return None

        lines = document.content.split("\n")
        for line_num, replacements in matches_by_line.items():
            line = lines[line_num - 1]
            # Process right-to-left to preserve column positions
            for col, expected, found in sorted(replacements, key=lambda r: r[0], reverse=True):
                idx = col - 1  # 0-indexed
                if line[idx : idx + len(found)] == found:
                    line = line[:idx] + expected + line[idx + len(found) :]
            lines[line_num - 1] = line

        return "\n".join(lines)

    @staticmethod
    def _in_exclusion_range(column: int, ranges: list[tuple[int, int]]) -> bool:
        """Check if a 1-indexed column is inside any (start, end) range."""
        for start, end in ranges:
            if start <= column < end:
                return True
        return False
