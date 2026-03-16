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

    def fix(self, document: Document, config: MD060Config) -> str | None:
        """Fix table column style by reformatting tables."""
        tables = self._find_tables(document)
        if not tables:
            return None

        lines = document.content.split("\n")
        changed = False

        for start_line, end_line in tables:
            rows: list[tuple[int, str]] = []
            for line_num in range(start_line, end_line + 1):
                line = document.get_line(line_num)
                if line is not None:
                    rows.append((line_num, line))

            if len(rows) < 2:
                continue

            style = config.style
            if style == "any":
                # Determine best style and skip if no violations
                style, error_count = self._determine_best_style(
                    document, rows, config.aligned_delimiter
                )
                if error_count == 0:
                    continue
            else:
                # Skip tables with no violations for the specific style
                table_violations = self._check_table(
                    document, (start_line, end_line), style, config.aligned_delimiter
                )
                if not table_violations:
                    continue

            # Parse all rows into cells
            parsed: list[tuple[int, list[str], bool, bool, bool]] = []
            for line_num, line in rows:
                cells, has_leading, has_trailing = self._split_cells(line)
                is_delim = self._is_delimiter_cells(cells)
                parsed.append((line_num, cells, has_leading, has_trailing, is_delim))

            # Calculate column widths for aligned style
            col_widths: list[int] | None = None
            if style == "aligned":
                col_widths = self._calc_col_widths(parsed)

            # Calculate header cell widths for aligned_delimiter option
            delim_widths: list[int] | None = None
            if config.aligned_delimiter and style in ("compact", "tight") and parsed:
                header_cells = parsed[0][1]
                delim_widths = [self._visual_width(c) for c in header_cells]

            # Format each row
            for line_num, cells, has_leading, has_trailing, is_delim in parsed:
                new_line = self._build_table_line(
                    cells,
                    has_leading,
                    has_trailing,
                    style,
                    col_widths=col_widths,
                    delim_widths=delim_widths if is_delim else None,
                    is_delim=is_delim,
                )
                if lines[line_num - 1] != new_line:
                    lines[line_num - 1] = new_line
                    changed = True

        return "\n".join(lines) if changed else None

    def _determine_best_style(
        self,
        document: Document,
        rows: list[tuple[int, str]],
        aligned_delimiter: bool,
    ) -> tuple[str, int]:
        """Determine which style produces fewest violations for a table.

        Returns:
            Tuple of (best_style_name, error_count).
        """
        errors_aligned = len(self._check_aligned_style(document, rows))

        if errors_aligned == 0:
            return "aligned", 0

        errors_compact = 0
        errors_tight = 0

        if aligned_delimiter and len(rows) >= 2:
            delim_errs = len(
                self._check_aligned_style(document, rows[:2], message=self.MSG_ALIGNED_DELIMITER)
            )
            errors_compact += delim_errs
            errors_tight += delim_errs

        for line_num, line in rows:
            compact_errs, tight_errs = self._check_compact_tight_style(document, line_num, line)
            errors_compact += len(compact_errs)
            errors_tight += len(tight_errs)

        candidates = [
            (errors_aligned, "aligned"),
            (errors_compact, "compact"),
            (errors_tight, "tight"),
        ]
        best = min(candidates, key=lambda x: x[0])
        return best[1], best[0]

    @staticmethod
    def _split_cells(line: str) -> tuple[list[str], bool, bool]:
        """Split a table line into trimmed cell contents.

        Returns:
            Tuple of (cells, has_leading_pipe, has_trailing_pipe).
        """
        stripped = line.strip()
        has_leading = stripped.startswith("|")
        has_trailing = len(stripped) > 1 and stripped.endswith("|")

        cells: list[str] = []
        current: list[str] = []
        i = 0
        while i < len(stripped):
            if stripped[i] == "\\" and i + 1 < len(stripped) and stripped[i + 1] == "|":
                current.append("\\|")
                i += 2
            elif stripped[i] == "|":
                cells.append("".join(current))
                current = []
                i += 1
            else:
                current.append(stripped[i])
                i += 1
        cells.append("".join(current))

        # Remove empty entries from leading/trailing pipes
        if has_leading and cells and cells[0].strip() == "":
            cells = cells[1:]
        if has_trailing and cells and cells[-1].strip() == "":
            cells = cells[:-1]

        cells = [c.strip() for c in cells]
        return cells, has_leading, has_trailing

    @staticmethod
    def _is_delimiter_cells(cells: list[str]) -> bool:
        """Check if cells represent a delimiter row."""
        return bool(cells) and all(c and set(c) <= {"-", ":"} and "-" in c for c in cells)

    def _calc_col_widths(self, parsed: list[tuple[int, list[str], bool, bool, bool]]) -> list[int]:
        """Calculate max visual width per column (excluding delimiter rows)."""
        max_widths: list[int] = []
        for _, cells, _, _, is_delim in parsed:
            if is_delim:
                continue
            for i, cell in enumerate(cells):
                w = self._visual_width(cell)
                if i >= len(max_widths):
                    max_widths.append(w)
                else:
                    max_widths[i] = max(max_widths[i], w)
        return max_widths

    def _build_table_line(
        self,
        cells: list[str],
        has_leading: bool,
        has_trailing: bool,
        style: str,
        col_widths: list[int] | None = None,
        delim_widths: list[int] | None = None,
        is_delim: bool = False,
    ) -> str:
        """Build a formatted table line from parsed cells."""
        n = len(cells)
        parts: list[str] = []

        for i, cell in enumerate(cells):
            is_first = i == 0
            is_last = i == n - 1

            # Determine formatted content
            if is_delim and delim_widths and i < len(delim_widths):
                content = self._format_delimiter_cell(cell, delim_widths[i])
            elif is_delim and style == "aligned" and col_widths and i < len(col_widths):
                content = self._format_delimiter_cell(cell, col_widths[i])
            elif style == "aligned" and col_widths and i < len(col_widths):
                padding = col_widths[i] - self._visual_width(cell)
                content = cell + " " * max(padding, 0)
            else:
                content = cell

            # Apply spacing
            if style == "tight":
                parts.append(content)
            else:  # compact or aligned
                has_left_pipe = has_leading or not is_first
                has_right_pipe = has_trailing or not is_last
                if content == "" and not is_delim:
                    parts.append(" " if (has_left_pipe or has_right_pipe) else "")
                else:
                    left = " " if has_left_pipe else ""
                    right = " " if has_right_pipe else ""
                    parts.append(f"{left}{content}{right}")

        result = "|".join(parts)
        if has_leading:
            result = "|" + result
        if has_trailing:
            result = result + "|"
        return result

    @staticmethod
    def _format_delimiter_cell(cell: str, width: int) -> str:
        """Format a delimiter cell to the specified width, preserving alignment markers."""
        left_colon = cell.startswith(":")
        right_colon = cell.endswith(":")

        dash_count = width
        if left_colon:
            dash_count -= 1
        if right_colon:
            dash_count -= 1
        dash_count = max(dash_count, 1)

        result = ""
        if left_colon:
            result += ":"
        result += "-" * dash_count
        if right_colon:
            result += ":"
        return result

    @staticmethod
    def _visual_width(text: str) -> int:
        """Calculate the visual width of text, accounting for wide characters."""
        width = 0
        for char in text:
            if unicodedata.east_asian_width(char) in ("W", "F"):
                width += 2
            else:
                width += 1
        return width

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
            visual_pos += MD060._visual_width(char)
        return result
