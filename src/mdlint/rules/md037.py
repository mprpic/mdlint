import re
from dataclasses import dataclass

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD037Config(RuleConfig):
    """Configuration for MD037 rule."""


class MD037(Rule[MD037Config]):
    """Spaces inside emphasis markers."""

    id = "MD037"
    name = "no-space-in-emphasis"
    summary = "Spaces inside emphasis markers"
    config_class = MD037Config

    description = (
        "This rule is triggered when emphasis markers (bold, italic) are used, "
        "but they have spaces between the markers and the text. For example, "
        "`** bold **` instead of `**bold**`."
    )

    rationale = (
        "Emphasis is only parsed as such when the asterisks or underscores are "
        "not surrounded by spaces. Extra spaces inside emphasis markers prevent "
        "the text from being properly rendered as bold or italic, and likely "
        "indicate the author intended to use emphasis formatting."
    )

    example_valid = """\
# Proper Emphasis

This text has **bold** and *italic* formatting.

You can also use __bold__ and _italic_ with underscores.

Multiple **bold words** in a sentence are *perfectly fine*.

Even ***bold and italic*** together works properly.
"""

    example_invalid = """\
# Improper Emphasis

This text has ** bold ** with spaces inside.

Here is * italic * with spaces too.

Underscores also fail: __ bold __ and _ italic _.
"""

    # Emphasis markers, longest first to avoid partial overlaps
    MARKERS = ["***", "**", "*", "___", "__", "_"]

    # Patterns for each marker: match exact marker + content + same marker.
    # Asterisks use [*\w] boundary to prevent matching inside words or longer runs.
    # Underscores use \w boundary (which includes _ itself) for the same purpose.
    _PATTERNS: dict[str, re.Pattern[str]] = {
        "***": re.compile(r"(?<![*\w])\*\*\*(?!\*)(.+?)(?<!\*)\*\*\*(?![*\w])"),
        "**": re.compile(r"(?<![*\w])\*\*(?!\*)(.+?)(?<!\*)\*\*(?![*\w])"),
        "*": re.compile(r"(?<![*\w])\*(?!\*)(.+?)(?<!\*)\*(?![*\w])"),
        "___": re.compile(r"(?<!\w)___(?!_)(.+?)(?<!_)___(?!\w)"),
        "__": re.compile(r"(?<!\w)__(?!_)(.+?)(?<!_)__(?!\w)"),
        "_": re.compile(r"(?<!\w)_(?!_)(.+?)(?<!_)_(?!\w)"),
    }

    def check(self, document: Document, config: MD037Config) -> list[Violation]:
        """Check for spaces inside emphasis markers."""
        violations: list[Violation] = []

        for token in document.tokens:
            if token.type != "inline" or not token.children or not token.map:
                continue

            current_line = token.map[0] + 1  # 1-indexed
            used_ranges: dict[int, list[tuple[int, int]]] = {}

            for child in token.children:
                if child.type in ("softbreak", "hardbreak"):
                    current_line += 1
                    continue
                if child.type != "text":
                    continue

                if "*" not in child.content and "_" not in child.content:
                    continue

                source_line = document.get_line(current_line)
                if not source_line:
                    continue

                for marker in self.MARKERS:
                    pattern = self._PATTERNS[marker]
                    for match in pattern.finditer(child.content):
                        match_text = match.group(0)
                        content = match.group(1)

                        has_leading_space = content[0].isspace()
                        has_trailing_space = content[-1].isspace()

                        if not has_leading_space and not has_trailing_space:
                            continue

                        # Verify match exists in source line (rejects escaped markers)
                        line_ranges = used_ranges.setdefault(current_line, [])
                        source_pos = self._find_in_source(match_text, source_line, line_ranges)
                        if source_pos < 0:
                            continue

                        line_ranges.append((source_pos, source_pos + len(match_text)))
                        column = source_pos + 1  # 1-indexed

                        if has_leading_space:
                            violations.append(
                                Violation(
                                    line=current_line,
                                    column=column,
                                    rule_id=self.id,
                                    rule_name=self.name,
                                    message=f"Spaces after opening emphasis marker: {marker}",
                                    context=source_line,
                                )
                            )

                        if has_trailing_space:
                            close_column = source_pos + len(match_text) - len(marker) + 1
                            violations.append(
                                Violation(
                                    line=current_line,
                                    column=close_column,
                                    rule_id=self.id,
                                    rule_name=self.name,
                                    message=f"Spaces before closing emphasis marker: {marker}",
                                    context=source_line,
                                )
                            )

        return violations

    def fix(self, document: Document, config: MD037Config) -> str | None:
        """Fix spaces inside emphasis markers by stripping them."""
        changed = False
        lines = document.content.split("\n")

        for token in document.tokens:
            if token.type != "inline" or not token.children or not token.map:
                continue

            current_line = token.map[0] + 1  # 1-indexed
            used_ranges: dict[int, list[tuple[int, int]]] = {}

            for child in token.children:
                if child.type in ("softbreak", "hardbreak"):
                    current_line += 1
                    continue
                if child.type != "text":
                    continue

                if "*" not in child.content and "_" not in child.content:
                    continue

                source_line = lines[current_line - 1]
                if not source_line:
                    continue

                for marker in self.MARKERS:
                    pattern = self._PATTERNS[marker]
                    for match in pattern.finditer(child.content):
                        match_text = match.group(0)
                        content = match.group(1)

                        has_leading_space = content[0].isspace()
                        has_trailing_space = content[-1].isspace()

                        if not has_leading_space and not has_trailing_space:
                            continue

                        line_ranges = used_ranges.setdefault(current_line, [])
                        source_pos = self._find_in_source(match_text, source_line, line_ranges)
                        if source_pos < 0:
                            continue

                        line_ranges.append((source_pos, source_pos + len(match_text)))

                        fixed_text = marker + content.strip() + marker
                        source_line = (
                            source_line[:source_pos]
                            + fixed_text
                            + source_line[source_pos + len(match_text) :]
                        )
                        lines[current_line - 1] = source_line

                        # Adjust used ranges for the length change
                        diff = len(fixed_text) - len(match_text)
                        if diff != 0:
                            line_ranges[-1] = (source_pos, source_pos + len(fixed_text))
                            for i in range(len(line_ranges) - 1):
                                s, e = line_ranges[i]
                                if s > source_pos:
                                    line_ranges[i] = (s + diff, e + diff)

                        changed = True

        if not changed:
            return None

        return "\n".join(lines)

    @staticmethod
    def _find_in_source(text: str, source_line: str, used_ranges: list[tuple[int, int]]) -> int:
        """Find text in source line, skipping already-used ranges."""
        start = 0
        while True:
            idx = source_line.find(text, start)
            if idx < 0:
                return -1
            end = idx + len(text)
            overlaps = False
            for r_start, r_end in used_ranges:
                if idx < r_end and end > r_start:
                    overlaps = True
                    break
            if not overlaps:
                return idx
            start = idx + 1
