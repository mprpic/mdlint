import unicodedata
from dataclasses import dataclass, field
from typing import Literal

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD060Config(RuleConfig):
    """Configuration for MD060 rule."""

    TableStyle = Literal["aligned", "any", "compact", "tight"]

    style: TableStyle = field(
        default="any",
        metadata={
            "description": "Required table column style.",
            "option_descriptions": {
                "any": "Allow any consistent style (reports fewest violations)",
                "aligned": "Pipes must be vertically aligned",
                "compact": "Single space around cell content",
                "tight": "No padding around cell content",
            },
        },
    )
    aligned_delimiter: bool = field(
        default=False,
        metadata={
            "description": "Require delimiter row pipes to align with header.",
        },
    )


class MD060(Rule[MD060Config]):
    """Table column style should be consistent."""

    id = "MD060"
    name = "table-column-style"
    summary = "Table column style should be consistent"
    config_class = MD060Config

    # Message constants
    MSG_ALIGNED = 'Table pipe does not align with header for style "aligned"'
    MSG_ALIGNED_DELIMITER = 'Table pipe does not align with header for option "aligned_delimiter"'
    MSG_COMPACT_EXTRA_LEFT = 'Table pipe has extra space to the left for style "compact"'
    MSG_COMPACT_MISSING_LEFT = 'Table pipe is missing space to the left for style "compact"'
    MSG_COMPACT_EXTRA_RIGHT = 'Table pipe has extra space to the right for style "compact"'
    MSG_COMPACT_MISSING_RIGHT = 'Table pipe is missing space to the right for style "compact"'
    MSG_TIGHT_LEFT = 'Table pipe has space to the left for style "tight"'
    MSG_TIGHT_RIGHT = 'Table pipe has space to the right for style "tight"'

    description = (
        "This rule checks that table column separator pipe characters (`|`) are "
        "used consistently. It supports three styles: `aligned` where pipes are "
        "vertically aligned (using visual width for CJK/emoji characters), "
        "`compact` with single space around content (empty cells may use a single "
        "space), and `tight` with no padding. The `any` style accepts any "
        "consistent style."
    )

    rationale = (
        "Consistent formatting makes it easier to understand a document. "
        "Well-formatted tables are easier to read and maintain."
    )

    example_valid = """\
# Valid Table Style

| Character | Meaning |
| --- | --- |
| Y | Yes |
| N | No |
"""

    example_invalid = """\
# Invalid Table Style

| Character | Meaning |
| --------- | ------- |
|Y | Yes|
| N | No |
"""

    def check(self, document: Document, config: MD060Config) -> list[Violation]:
        """Check for table column style violations."""
        violations: list[Violation] = []

        style = config.style
        aligned_delimiter = config.aligned_delimiter

        # Find all tables in the document
        tables = self._find_tables(document)

        for table in tables:
            violations.extend(self._check_table(document, table, style, aligned_delimiter))

        return violations

    def _find_tables(self, document: Document) -> list[tuple[int, int]]:
        """Find all tables and their line ranges.

        Returns:
            List of (start_line, end_line) tuples for each table (1-indexed).
        """
        tables: list[tuple[int, int]] = []

        for token in document.tokens:
            if token.type == "table_open" and token.map:
                start_line = token.map[0] + 1  # Convert to 1-indexed
                end_line = token.map[1]  # Already exclusive, so this is the last line
                tables.append((start_line, end_line))

        return tables

    def _check_table(
        self,
        document: Document,
        table_range: tuple[int, int],
        style: str,
        aligned_delimiter: bool,
    ) -> list[Violation]:
        """Check a single table for style violations.

        Args:
            document: The document being checked.
            table_range: (start_line, end_line) tuple.
            style: The required style.
            aligned_delimiter: Whether delimiter row must align with header.

        Returns:
            List of violations for this table.
        """
        start_line, end_line = table_range

        # Get all table rows
        rows: list[tuple[int, str]] = []
        for line_num in range(start_line, end_line + 1):
            line = document.get_line(line_num)
            if line is not None:
                rows.append((line_num, line))

        if len(rows) < 2:
            return []

        # Determine styles allowed
        style_aligned_allowed = style in ("any", "aligned")
        style_compact_allowed = style in ("any", "compact")
        style_tight_allowed = style in ("any", "tight")

        # Calculate errors for each style
        errors_aligned: list[Violation] = []
        errors_compact: list[Violation] = []
        errors_tight: list[Violation] = []

        if style_aligned_allowed:
            errors_aligned = self._check_aligned_style(document, rows)

        if style_compact_allowed or style_tight_allowed:
            # Skip compact/tight checks if aligned has no errors
            if not (style_aligned_allowed and len(errors_aligned) == 0):
                if aligned_delimiter and len(rows) >= 2:
                    # Check delimiter alignment with header
                    delim_errs = self._check_aligned_style(
                        document, rows[:2], message=self.MSG_ALIGNED_DELIMITER
                    )
                    errors_compact.extend(delim_errs)
                    errors_tight.extend(delim_errs)

                for line_num, line in rows:
                    compact_errs, tight_errs = self._check_compact_tight_style(
                        document, line_num, line
                    )
                    errors_compact.extend(compact_errs)
                    errors_tight.extend(tight_errs)

        # Return errors for the allowed style with fewest violations
        candidates: list[list[Violation]] = []
        if style_aligned_allowed:
            candidates.append(errors_aligned)
        if style_compact_allowed:
            candidates.append(errors_compact)
        if style_tight_allowed:
            candidates.append(errors_tight)

        return min(candidates, key=len) if candidates else []  # type: ignore[return-value]

    def _check_aligned_style(
        self,
        document: Document,
        rows: list[tuple[int, str]],
        message: str | None = None,
    ) -> list[Violation]:
        """Check if table pipes are vertically aligned.

        Args:
            document: The document being checked.
            rows: List of (line_number, line_content) tuples.
            message: Custom violation message (defaults to MSG_ALIGNED).

        Returns:
            List of violations for misaligned pipes.
        """
        violations: list[Violation] = []
        msg = message or self.MSG_ALIGNED

        if not rows:
            return violations

        # Get pipe info (char_index, visual_position) from header row
        _, header_line = rows[0]
        header_info = self._get_pipe_info(header_line)

        if not header_info:
            return violations

        header_visual_positions = [vp for _, vp in header_info]

        # Check all other rows
        for line_num, line in rows[1:]:
            row_info = self._get_pipe_info(line)

            # Compare visual positions
            for i, (char_idx, visual_pos) in enumerate(row_info):
                if i < len(header_visual_positions):
                    if visual_pos != header_visual_positions[i]:
                        violations.append(
                            Violation(
                                line=line_num,
                                column=char_idx + 1,
                                rule_id=self.id,
                                rule_name=self.name,
                                message=msg,
                                context=document.get_line(line_num),
                            )
                        )

        return violations

    def _check_compact_tight_style(
        self, document: Document, line_num: int, line: str
    ) -> tuple[list[Violation], list[Violation]]:
        """Check line for compact and tight style violations.

        Args:
            document: The document being checked.
            line_num: Line number.
            line: Line content.

        Returns:
            Tuple of (compact_violations, tight_violations).
        """
        compact_violations: list[Violation] = []
        tight_violations: list[Violation] = []

        # Find pipe positions (skip escaped pipes)
        i = 0
        while i < len(line):
            if line[i] == "|" and (i == 0 or line[i - 1] != "\\"):
                col = i + 1  # 1-indexed column

                # Check space to the left (if not at start of line)
                if i > 0:
                    left_char = line[i - 1]
                    if left_char == " ":
                        # Check for extra spaces (more than one)
                        spaces_left = 0
                        j = i - 1
                        while j >= 0 and line[j] == " ":
                            spaces_left += 1
                            j -= 1
                        if spaces_left > 1:
                            compact_violations.append(
                                Violation(
                                    line=line_num,
                                    column=col,
                                    rule_id=self.id,
                                    rule_name=self.name,
                                    message=self.MSG_COMPACT_EXTRA_LEFT,
                                    context=document.get_line(line_num),
                                )
                            )
                        # Tight doesn't allow any space
                        tight_violations.append(
                            Violation(
                                line=line_num,
                                column=col,
                                rule_id=self.id,
                                rule_name=self.name,
                                message=self.MSG_TIGHT_LEFT,
                                context=document.get_line(line_num),
                            )
                        )
                    elif left_char not in ("|", "-", ":"):
                        # Missing space for compact
                        compact_violations.append(
                            Violation(
                                line=line_num,
                                column=col,
                                rule_id=self.id,
                                rule_name=self.name,
                                message=self.MSG_COMPACT_MISSING_LEFT,
                                context=document.get_line(line_num),
                            )
                        )

                # Check space to the right (if not at end of line)
                if i < len(line) - 1:
                    right_char = line[i + 1]
                    is_trailing = i == len(line.rstrip()) - 1

                    if not is_trailing:
                        if right_char == " ":
                            # Check for extra spaces
                            spaces_right = 0
                            j = i + 1
                            while j < len(line) and line[j] == " ":
                                spaces_right += 1
                                j += 1
                            # Allow trailing space at end of cell
                            if j < len(line) and line[j] != "|":
                                if spaces_right > 1:
                                    compact_violations.append(
                                        Violation(
                                            line=line_num,
                                            column=col,
                                            rule_id=self.id,
                                            rule_name=self.name,
                                            message=self.MSG_COMPACT_EXTRA_RIGHT,
                                            context=document.get_line(line_num),
                                        )
                                    )
                            # Tight doesn't allow any space (except trailing)
                            if not is_trailing:
                                tight_violations.append(
                                    Violation(
                                        line=line_num,
                                        column=col,
                                        rule_id=self.id,
                                        rule_name=self.name,
                                        message=self.MSG_TIGHT_RIGHT,
                                        context=document.get_line(line_num),
                                    )
                                )
                        elif right_char not in ("|", "-", ":"):
                            # Missing space for compact (unless it's a delimiter char)
                            compact_violations.append(
                                Violation(
                                    line=line_num,
                                    column=col,
                                    rule_id=self.id,
                                    rule_name=self.name,
                                    message=self.MSG_COMPACT_MISSING_RIGHT,
                                    context=document.get_line(line_num),
                                )
                            )
            i += 1

        return compact_violations, tight_violations

    @staticmethod
    def _get_pipe_info(line: str) -> list[tuple[int, int]]:
        """Get character index and visual position of unescaped pipes.

        Uses visual width to handle CJK/emoji characters that occupy two
        columns in a monospace terminal.

        Args:
            line: Line content.

        Returns:
            List of (char_index, visual_position) tuples for each unescaped pipe.
        """
        result: list[tuple[int, int]] = []
        visual_pos = 0
        for i, char in enumerate(line):
            if char == "|" and (i == 0 or line[i - 1] != "\\"):
                result.append((i, visual_pos))
            # CJK and fullwidth characters take 2 visual columns
            if unicodedata.east_asian_width(char) in ("W", "F"):
                visual_pos += 2
            else:
                visual_pos += 1
        return result
