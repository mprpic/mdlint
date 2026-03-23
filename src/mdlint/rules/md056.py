import re
from dataclasses import dataclass

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD056Config(RuleConfig):
    """Configuration for MD056 rule."""


class MD056(Rule[MD056Config]):
    """Table column count should be consistent."""

    id = "MD056"
    name = "table-column-count"
    summary = "Table column count should be consistent"
    config_class = MD056Config

    description = (
        "This rule is triggered when a GitHub Flavored Markdown table does not "
        "have the same number of cells in every row. Each row should have the "
        "same number of cells as the header row. Note that a table's header row "
        "and its delimiter row must have the same number of cells or it will not "
        "be recognized as a table (per the GFM specification)."
    )

    rationale = (
        "Extra cells in a row are usually not shown, so their data is lost. "
        "Missing cells in a row create holes in the table and suggest an omission. "
        "Consistent column counts ensure all data is visible and properly aligned."
    )

    example_valid = """\
# Valid Table

| Header | Header |
| ------ | ------ |
| Cell   | Cell   |
| Cell   | Cell   |
| Cell   | Cell   |
"""

    example_invalid = """\
# Invalid Table

| Header | Header |
| ------ | ------ |
| Cell   | Cell   |
| Cell   |
| Cell   | Cell   | Cell   |
"""

    # Matches unescaped pipe characters (not preceded by backslash)
    _UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")

    @staticmethod
    def _count_cells(line: str, pattern: re.Pattern[str]) -> int:
        """Count the number of cells in a table row."""
        stripped = line.strip()
        # Remove leading pipe if present
        if stripped.startswith("|"):
            stripped = stripped[1:]
        # Remove trailing pipe if present
        if stripped.endswith("|") and not stripped.endswith("\\|"):
            stripped = stripped[:-1]
        cells = pattern.split(stripped)
        return len(cells)

    @staticmethod
    def _is_delimiter_row(line: str) -> bool:
        """Check if a line is a table delimiter row."""
        return all(c in "-:| " for c in line.strip())

    def check(self, document: Document, config: MD056Config) -> list[Violation]:
        """Check for table column count violations."""
        violations: list[Violation] = []

        for token in document.tokens:
            if token.type == "table_open" and token.map:
                table_start, table_end = token.map
                expected_count: int | None = None

                for line_num in range(table_start + 1, table_end + 1):
                    line = document.get_line(line_num)
                    if not line:
                        continue

                    if self._is_delimiter_row(line):
                        continue

                    if not self._UNESCAPED_PIPE.search(line):
                        continue

                    actual_count = self._count_cells(line, self._UNESCAPED_PIPE)

                    if expected_count is None:
                        expected_count = actual_count
                        continue

                    if actual_count < expected_count:
                        violations.append(
                            Violation(
                                line=line_num,
                                column=1,
                                rule_id=self.id,
                                rule_name=self.name,
                                message=(
                                    f"Too few cells, row will be missing data. "
                                    f"Expected {expected_count}, found {actual_count}"
                                ),
                                context=line,
                            )
                        )
                    elif actual_count > expected_count:
                        violations.append(
                            Violation(
                                line=line_num,
                                column=1,
                                rule_id=self.id,
                                rule_name=self.name,
                                message=(
                                    f"Too many cells, extra data will be missing. "
                                    f"Expected {expected_count}, found {actual_count}"
                                ),
                                context=line,
                            )
                        )

        return violations
