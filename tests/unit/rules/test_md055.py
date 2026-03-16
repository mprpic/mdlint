from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md055 import MD055, MD055Config
from tests.conftest import load_fixture


class TestMD055:
    @pytest.fixture
    def rule(self) -> MD055:
        return MD055()

    @pytest.fixture
    def config(self) -> MD055Config:
        return MD055Config()

    def test_valid_document(self, rule: MD055, config: MD055Config) -> None:
        """Valid document with consistent table pipe style."""
        content = load_fixture("md055", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD055, config: MD055Config) -> None:
        """Invalid document with inconsistent table pipe style."""
        content = load_fixture("md055", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].rule_id == "MD055"
        assert violations[0].line == 4
        assert violations[0].column == len("| -------- | --------")
        assert violations[0].message == "Missing trailing pipe"
        assert violations[1].line == 5
        assert violations[1].column == 1
        assert violations[1].message == "Missing leading pipe"

    def test_no_tables(self, rule: MD055, config: MD055Config) -> None:
        """Document without tables passes."""
        content = "# Heading\n\nJust some text, no tables.\n"
        doc = Document(Path("no_tables.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_single_row_table(self, rule: MD055, config: MD055Config) -> None:
        """Single row table with consistent style passes."""
        content = """\
| Header 1 | Header 2 |
| -------- | -------- |
| Cell 1   | Cell 2   |
"""
        doc = Document(Path("single_row.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_no_leading_or_trailing_consistent(self, rule: MD055, config: MD055Config) -> None:
        """Table without leading or trailing pipes is consistent."""
        content = """\
Header 1 | Header 2
-------- | --------
Cell 1   | Cell 2
"""
        doc = Document(Path("no_pipes.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_leading_only_consistent(self, rule: MD055, config: MD055Config) -> None:
        """Table with leading pipes only is consistent."""
        content = """\
| Header 1 | Header 2
| -------- | --------
| Cell 1   | Cell 2
"""
        doc = Document(Path("leading_only.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_trailing_only_consistent(self, rule: MD055, config: MD055Config) -> None:
        """Table with trailing pipes only is consistent."""
        content = """\
Header 1 | Header 2 |
-------- | -------- |
Cell 1   | Cell 2   |
"""
        doc = Document(Path("trailing_only.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_missing_trailing_pipe(self, rule: MD055, config: MD055Config) -> None:
        """Table row missing trailing pipe is detected."""
        content = """\
| Header 1 | Header 2 |
| -------- | --------
| Cell 1   | Cell 2   |
"""
        doc = Document(Path("missing_trailing.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 2
        assert violations[0].column == len("| -------- | --------")
        assert violations[0].message == "Missing trailing pipe"

    def test_missing_leading_pipe(self, rule: MD055, config: MD055Config) -> None:
        """Table row missing leading pipe is detected."""
        content = """\
| Header 1 | Header 2 |
| -------- | -------- |
  Cell 1   | Cell 2   |
"""
        doc = Document(Path("missing_leading.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3
        assert violations[0].column == 1
        assert violations[0].message == "Missing leading pipe"

    def test_style_leading_and_trailing(self, rule: MD055) -> None:
        """Leading and trailing style requires pipes on both ends."""
        config = MD055Config(style="leading_and_trailing")
        content = """\
Header 1 | Header 2
-------- | --------
Cell 1   | Cell 2
"""
        doc = Document(Path("no_pipes.md"), content)

        violations = rule.check(doc, config)

        # All 3 rows should have violations for missing both leading and trailing
        assert len(violations) == 6

    def test_style_no_leading_or_trailing(self, rule: MD055) -> None:
        """No leading or trailing style requires no pipes on either end."""
        config = MD055Config(style="no_leading_or_trailing")
        content = """\
| Header 1 | Header 2 |
| -------- | -------- |
| Cell 1   | Cell 2   |
"""
        doc = Document(Path("with_pipes.md"), content)

        violations = rule.check(doc, config)

        # All 3 rows should have violations for having both leading and trailing
        assert len(violations) == 6

    def test_style_leading_only(self, rule: MD055) -> None:
        """Leading only style requires leading pipes but no trailing pipes."""
        config = MD055Config(style="leading_only")
        content = """\
| Header 1 | Header 2 |
| -------- | -------- |
| Cell 1   | Cell 2   |
"""
        doc = Document(Path("with_pipes.md"), content)

        violations = rule.check(doc, config)

        # All 3 rows have trailing pipes (unexpected)
        assert len(violations) == 3
        assert all("trailing" in v.message.lower() for v in violations)

    def test_style_trailing_only(self, rule: MD055) -> None:
        """Trailing only style requires trailing pipes but no leading pipes."""
        config = MD055Config(style="trailing_only")
        content = """\
| Header 1 | Header 2 |
| -------- | -------- |
| Cell 1   | Cell 2   |
"""
        doc = Document(Path("with_pipes.md"), content)

        violations = rule.check(doc, config)

        # All 3 rows have leading pipes (unexpected)
        assert len(violations) == 3
        assert all("leading" in v.message.lower() for v in violations)

    def test_multiple_tables_consistent(self, rule: MD055, config: MD055Config) -> None:
        """Multiple tables with consistent style passes."""
        content = """\
| Table 1 A | Table 1 B |
| --------- | --------- |
| Cell 1    | Cell 2    |

| Table 2 A | Table 2 B |
| --------- | --------- |
| Cell 3    | Cell 4    |
"""
        doc = Document(Path("multiple_tables.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_tables_inconsistent_across_tables(
        self, rule: MD055, config: MD055Config
    ) -> None:
        """Style set by first table enforces on subsequent tables."""
        content = """\
| Table 1 A | Table 1 B |
| --------- | --------- |
| Cell 1    | Cell 2    |

Table 2 A | Table 2 B
--------- | ---------
Cell 3    | Cell 4
"""
        doc = Document(Path("inconsistent_tables.md"), content)

        violations = rule.check(doc, config)

        # Second table: 3 rows each missing both leading and trailing pipes
        assert len(violations) == 6

    def test_blockquote_table_consistent(self, rule: MD055, config: MD055Config) -> None:
        """Table inside a blockquote with consistent pipes passes."""
        content = load_fixture("md055", "blockquote_consistent.md")
        doc = Document(Path("blockquote_consistent.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_blockquote_table_inconsistent(self, rule: MD055, config: MD055Config) -> None:
        """Table inside a blockquote with inconsistent pipes is detected."""
        content = load_fixture("md055", "blockquote_inconsistent.md")
        doc = Document(Path("blockquote_inconsistent.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].line == 2
        assert violations[0].message == "Missing trailing pipe"
        assert violations[1].line == 3
        assert violations[1].message == "Missing leading pipe"

    def test_nested_blockquote_table(self, rule: MD055, config: MD055Config) -> None:
        """Table inside a nested blockquote with consistent pipes passes."""
        content = load_fixture("md055", "nested_blockquote.md")
        doc = Document(Path("nested_blockquote.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_list_item_table(self, rule: MD055, config: MD055Config) -> None:
        """Table inside a list item with consistent pipes passes."""
        content = load_fixture("md055", "list_item.md")
        doc = Document(Path("list_item.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_fix_corrects_invalid(self, rule: MD055, config: MD055Config) -> None:
        """Fixing invalid content produces valid output."""
        content = load_fixture("md055", "invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        # The first row has leading+trailing, so fix should add missing pipes
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_returns_none_for_valid(self, rule: MD055, config: MD055Config) -> None:
        """Fixing already-valid content returns None."""
        content = load_fixture("md055", "valid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_missing_trailing_pipe(self, rule: MD055, config: MD055Config) -> None:
        """Fix adds missing trailing pipe."""
        content = """\
| Header 1 | Header 2 |
| -------- | --------
| Cell 1   | Cell 2   |
"""
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert "| -------- | -------- |" in result

    def test_fix_missing_leading_pipe(self, rule: MD055, config: MD055Config) -> None:
        """Fix adds missing leading pipe."""
        content = """\
| Header 1 | Header 2 |
| -------- | -------- |
  Cell 1   | Cell 2   |
"""
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert "| Cell 1   | Cell 2   |" in result

    def test_fix_style_leading_and_trailing(self, rule: MD055) -> None:
        """Fix adds leading and trailing pipes when style requires them."""
        config = MD055Config(style="leading_and_trailing")
        content = """\
Header 1 | Header 2
-------- | --------
Cell 1   | Cell 2
"""
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_style_no_leading_or_trailing(self, rule: MD055) -> None:
        """Fix removes leading and trailing pipes when style forbids them."""
        config = MD055Config(style="no_leading_or_trailing")
        content = """\
| Header 1 | Header 2 |
| -------- | -------- |
| Cell 1   | Cell 2   |
"""
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_blockquote_inconsistent(self, rule: MD055, config: MD055Config) -> None:
        """Fix handles tables inside blockquotes."""
        content = load_fixture("md055", "blockquote_inconsistent.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_multiple_tables_inconsistent(self, rule: MD055, config: MD055Config) -> None:
        """Fix handles multiple tables with inconsistent styles."""
        content = """\
| Table 1 A | Table 1 B |
| --------- | --------- |
| Cell 1    | Cell 2    |

Table 2 A | Table 2 B
--------- | ---------
Cell 3    | Cell 4
"""
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []
