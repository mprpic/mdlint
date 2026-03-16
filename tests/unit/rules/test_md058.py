from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md058 import MD058, MD058Config
from tests.conftest import load_fixture


class TestMD058:
    @pytest.fixture
    def rule(self) -> MD058:
        return MD058()

    @pytest.fixture
    def config(self) -> MD058Config:
        return MD058Config()

    def test_valid_document(self, rule: MD058, config: MD058Config) -> None:
        """Valid document passes the rule."""
        content = load_fixture("md058", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD058, config: MD058Config) -> None:
        """Invalid document triggers violations."""
        content = load_fixture("md058", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].rule_id == "MD058"
        # Missing blank line above table
        assert violations[0].line == 2
        assert "preceded" in violations[0].message.lower()
        # Missing blank line below table
        assert violations[1].line == 4
        assert "followed" in violations[1].message.lower()

    def test_no_blank_line_above(self, rule: MD058, config: MD058Config) -> None:
        """Table without blank line above triggers violation."""
        content = "Some text.\n| A | B |\n|---|---|\n| 1 | 2 |\n\nMore text.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 2
        assert "preceded" in violations[0].message.lower()

    def test_no_blank_line_below(self, rule: MD058, config: MD058Config) -> None:
        """Table without blank line below triggers violation."""
        # Use a blockquote after the table since plain text is absorbed into the table
        content = "Some text.\n\n| A | B |\n|---|---|\n| 1 | 2 |\n> Quote\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 5
        assert "followed" in violations[0].message.lower()

    def test_table_at_start(self, rule: MD058, config: MD058Config) -> None:
        """Table at start of document doesn't need blank line above."""
        content = "| A | B |\n|---|---|\n| 1 | 2 |\n\nSome text.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_table_at_end(self, rule: MD058, config: MD058Config) -> None:
        """Table at end of document doesn't need blank line below."""
        content = "Some text.\n\n| A | B |\n|---|---|\n| 1 | 2 |\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_tables_valid(self, rule: MD058, config: MD058Config) -> None:
        """Multiple tables all properly spaced."""
        content = (
            "Text.\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n"
            "More text.\n\n| C | D |\n|---|---|\n| 3 | 4 |\n\nEnd text.\n"
        )
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_tables_invalid(self, rule: MD058, config: MD058Config) -> None:
        """Multiple tables with missing blank lines."""
        # First table: no blank line above (preceded by text), no blank below (blockquote)
        # Second table: has blank line above, no blank below (blockquote)
        content = (
            "Text.\n| A | B |\n|---|---|\n| 1 | 2 |\n"
            "> Quote\n\n| C | D |\n|---|---|\n| 3 | 4 |\n> End.\n"
        )
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        # First table: missing above and below (2 violations)
        # Second table: missing below only (1 violation, has blank line above)
        assert len(violations) == 3
        assert violations[0].line == 2  # First table missing blank above
        assert violations[1].line == 4  # First table missing blank below
        assert violations[2].line == 9  # Second table missing blank below

    def test_column_is_one(self, rule: MD058, config: MD058Config) -> None:
        """Column should always be 1 for blank line violations."""
        content = "Some text.\n| A | B |\n|---|---|\n| 1 | 2 |\n\nMore text.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].column == 1

    def test_context_shows_table_line(self, rule: MD058, config: MD058Config) -> None:
        """Violation context should show the table line."""
        content = "Some text.\n| A | B |\n|---|---|\n| 1 | 2 |\n\nMore text.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "|" in violations[0].context

    def test_table_with_alignment(self, rule: MD058, config: MD058Config) -> None:
        """Table with alignment markers."""
        content = (
            "Some text.\n\n"
            "| Left | Center | Right |\n"
            "|:-----|:------:|------:|\n"
            "| A    | B      | C     |\n\n"
            "More text.\n"
        )
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_table_after_heading(self, rule: MD058, config: MD058Config) -> None:
        """Table after heading needs blank line."""
        content = "# Heading\n| A | B |\n|---|---|\n| 1 | 2 |\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 2
        assert "preceded" in violations[0].message.lower()

    def test_table_after_list(self, rule: MD058, config: MD058Config) -> None:
        """Table after list needs blank line."""
        # List followed by blank line, then table - should be valid
        content = "- Item 1\n- Item 2\n\n| A | B |\n|---|---|\n| 1 | 2 |\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_table_before_blockquote_no_blank(self, rule: MD058, config: MD058Config) -> None:
        """Table before blockquote without blank line triggers violation."""
        content = "# Title\n\n| A | B |\n|---|---|\n| 1 | 2 |\n> Quote\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "followed" in violations[0].message.lower()

    def test_table_in_blockquote(self, rule: MD058, config: MD058Config) -> None:
        """Table as only content inside a blockquote has no violations."""
        content = "> | A | B |\n> |---|---|\n> | 1 | 2 |\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_table_in_blockquote_after_text(self, rule: MD058, config: MD058Config) -> None:
        """Table after text inside a blockquote without blank line triggers violation."""
        content = "> Text\n> | A | B |\n> |---|---|\n> | 1 | 2 |\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 2
        assert "preceded" in violations[0].message.lower()

    def test_back_to_back_tables_with_blank_line(self, rule: MD058, config: MD058Config) -> None:
        """Two adjacent tables separated by a blank line have no violations."""
        content = "| A | B |\n|---|---|\n| 1 | 2 |\n\n| C | D |\n|---|---|\n| 3 | 4 |\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_back_to_back_tables_without_blank_line(self, rule: MD058, config: MD058Config) -> None:
        """Two tables separated by a heading without blank lines trigger violations."""
        content = "| A | B |\n|---|---|\n| 1 | 2 |\n# Heading\n| C | D |\n|---|---|\n| 3 | 4 |\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].line == 3
        assert "followed" in violations[0].message.lower()
        assert violations[1].line == 5
        assert "preceded" in violations[1].message.lower()

    def test_only_table_in_document(self, rule: MD058, config: MD058Config) -> None:
        """Document containing only a table has no violations."""
        content = "| A | B |\n|---|---|\n| 1 | 2 |\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_table_after_front_matter(self, rule: MD058, config: MD058Config) -> None:
        """Table immediately after front matter without blank line triggers violation."""
        content = "---\ntitle: Test\n---\n| A | B |\n|---|---|\n| 1 | 2 |\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 4
        assert "preceded" in violations[0].message.lower()

    def test_fix_corrects_invalid(self, rule: MD058, config: MD058Config) -> None:
        """Fix inserts blank lines around tables in invalid document."""
        content = load_fixture("md058", "invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_returns_none_for_valid(self, rule: MD058, config: MD058Config) -> None:
        """Fix returns None when document is already valid."""
        content = load_fixture("md058", "valid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_missing_blank_above(self, rule: MD058, config: MD058Config) -> None:
        """Fix inserts blank line above table."""
        content = "Some text.\n| A | B |\n|---|---|\n| 1 | 2 |\n\nMore text.\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert result == "Some text.\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\nMore text.\n"

    def test_fix_missing_blank_below(self, rule: MD058, config: MD058Config) -> None:
        """Fix inserts blank line below table."""
        content = "Some text.\n\n| A | B |\n|---|---|\n| 1 | 2 |\n> Quote\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert result == "Some text.\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n> Quote\n"

    def test_fix_multiple_tables(self, rule: MD058, config: MD058Config) -> None:
        """Fix inserts blank lines around multiple tables."""
        content = (
            "Text.\n| A | B |\n|---|---|\n| 1 | 2 |\n"
            "> Quote\n\n| C | D |\n|---|---|\n| 3 | 4 |\n> End.\n"
        )
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_table_at_start_and_end(self, rule: MD058, config: MD058Config) -> None:
        """Fix returns None for table at start/end of document (no blank lines needed)."""
        content = "| A | B |\n|---|---|\n| 1 | 2 |\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_table_after_heading(self, rule: MD058, config: MD058Config) -> None:
        """Fix inserts blank line between heading and table."""
        content = "# Heading\n| A | B |\n|---|---|\n| 1 | 2 |\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert result == "# Heading\n\n| A | B |\n|---|---|\n| 1 | 2 |\n"

    def test_fix_back_to_back_tables_with_heading(self, rule: MD058, config: MD058Config) -> None:
        """Fix inserts blank lines around tables separated by heading."""
        content = "| A | B |\n|---|---|\n| 1 | 2 |\n# Heading\n| C | D |\n|---|---|\n| 3 | 4 |\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []
