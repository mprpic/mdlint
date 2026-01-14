from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md056 import MD056, MD056Config
from tests.conftest import load_fixture


class TestMD056:
    @pytest.fixture
    def rule(self) -> MD056:
        return MD056()

    @pytest.fixture
    def config(self) -> MD056Config:
        return MD056Config()

    def test_valid_table(self, rule: MD056, config: MD056Config) -> None:
        """Valid table with consistent column count."""
        content = load_fixture("md056", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_table(self, rule: MD056, config: MD056Config) -> None:
        """Invalid table with inconsistent column count."""
        content = load_fixture("md056", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].rule_id == "MD056"
        assert violations[0].line == 6
        assert "Too few cells" in violations[0].message
        assert violations[1].line == 7
        assert "Too many cells" in violations[1].message

    def test_no_tables(self, rule: MD056, config: MD056Config) -> None:
        """Document without any tables."""
        content = load_fixture("md056", "no_tables.md")
        doc = Document(Path("no_tables.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_tables(self, rule: MD056, config: MD056Config) -> None:
        """Multiple tables with different column counts."""
        content = load_fixture("md056", "multiple_tables.md")
        doc = Document(Path("multiple_tables.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_table_without_pipes_at_ends(self, rule: MD056, config: MD056Config) -> None:
        """Table without leading/trailing pipes (GFM allows this)."""
        content = load_fixture("md056", "no_outer_pipes.md")
        doc = Document(Path("no_outer_pipes.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_single_column_table(self, rule: MD056, config: MD056Config) -> None:
        """Single column table."""
        content = load_fixture("md056", "single_column.md")
        doc = Document(Path("single_column.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_too_few_cells_specific_message(self, rule: MD056, config: MD056Config) -> None:
        """Too few cells shows expected vs actual count."""
        content = load_fixture("md056", "too_few.md")
        doc = Document(Path("too_few.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "Expected 3, found 1" in violations[0].message

    def test_too_many_cells_specific_message(self, rule: MD056, config: MD056Config) -> None:
        """Too many cells shows expected vs actual count."""
        content = load_fixture("md056", "too_many.md")
        doc = Document(Path("too_many.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "Expected 2, found 4" in violations[0].message

    def test_escaped_pipe(self, rule: MD056, config: MD056Config) -> None:
        """Escaped pipe in cell content is not a column separator."""
        content = load_fixture("md056", "escaped_pipe.md")
        doc = Document(Path("escaped_pipe.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_empty_cells(self, rule: MD056, config: MD056Config) -> None:
        """Empty cells still count as cells."""
        content = load_fixture("md056", "empty_cells.md")
        doc = Document(Path("empty_cells.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_header_only_table(self, rule: MD056, config: MD056Config) -> None:
        """Table with only header and delimiter rows."""
        content = load_fixture("md056", "header_only.md")
        doc = Document(Path("header_only.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0
