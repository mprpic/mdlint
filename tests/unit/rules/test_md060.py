from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md060 import MD060, MD060Config
from tests.conftest import load_fixture


def _table_cells(content: str) -> list[list[list[str]]]:
    """Cell text of every table, so tests can prove a fix kept the table intact."""
    tables: list[list[list[str]]] = []
    in_table = False
    for token in Document(Path("test.md"), content).tokens:
        if token.type == "table_open":
            tables.append([])
            in_table = True
        elif token.type == "table_close":
            in_table = False
        elif in_table and token.type == "tr_open":
            tables[-1].append([])
        elif in_table and token.type == "inline":
            tables[-1][-1].append(token.content)
    return tables


def _apply_fix(rule: MD060, content: str, config: MD060Config) -> str:
    result = rule.fix(Document(Path("test.md"), content), config)
    return content if result is None else result


class TestMD060:
    @pytest.fixture
    def rule(self) -> MD060:
        return MD060()

    @pytest.fixture
    def config(self) -> MD060Config:
        return MD060Config()

    def test_valid_aligned_table(self, rule: MD060, config: MD060Config) -> None:
        """Valid document with aligned table columns."""
        content = load_fixture("md060", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_mixed_styles(self, rule: MD060, config: MD060Config) -> None:
        """Invalid document with mixed table column styles."""
        content = load_fixture("md060", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].line == 5
        assert violations[0].column == 1
        assert violations[0].message == MD060.MSG_COMPACT_MISSING_RIGHT
        assert violations[1].line == 5
        assert violations[1].column == 9
        assert violations[1].message == MD060.MSG_COMPACT_MISSING_LEFT

    def test_no_table(self, rule: MD060, config: MD060Config) -> None:
        """Document without tables."""
        content = load_fixture("md060", "no_table.md")
        doc = Document(Path("no_table.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_aligned_style(self, rule: MD060) -> None:
        """Aligned style table passes with aligned style config."""
        config = MD060Config(style="aligned")
        content = load_fixture("md060", "aligned.md")
        doc = Document(Path("aligned.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_compact_style(self, rule: MD060) -> None:
        """Compact style table passes with compact style config."""
        config = MD060Config(style="compact")
        content = load_fixture("md060", "compact.md")
        doc = Document(Path("compact.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_tight_style(self, rule: MD060) -> None:
        """Tight style table passes with tight style config."""
        config = MD060Config(style="tight")
        content = load_fixture("md060", "tight.md")
        doc = Document(Path("tight.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_aligned_style_violation(self, rule: MD060) -> None:
        """Compact table fails with aligned style config."""
        config = MD060Config(style="aligned")
        content = load_fixture("md060", "compact.md")
        doc = Document(Path("compact.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 6
        assert violations[0].line == 4
        assert violations[0].column == 7
        assert violations[0].message == MD060.MSG_ALIGNED

    def test_compact_style_violation(self, rule: MD060) -> None:
        """Tight table fails with compact style config."""
        config = MD060Config(style="compact")
        content = load_fixture("md060", "tight.md")
        doc = Document(Path("tight.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 12
        assert violations[0].line == 3
        assert violations[0].column == 1
        assert violations[0].message == MD060.MSG_COMPACT_MISSING_RIGHT

    def test_tight_style_violation(self, rule: MD060) -> None:
        """Compact table fails with tight style config."""
        config = MD060Config(style="tight")
        content = load_fixture("md060", "compact.md")
        doc = Document(Path("compact.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 16
        assert violations[0].line == 3
        assert violations[0].column == 1
        assert violations[0].message == MD060.MSG_TIGHT_RIGHT

    def test_aligned_delimiter(self, rule: MD060) -> None:
        """Table with aligned delimiter row passes."""
        config = MD060Config(style="compact", aligned_delimiter=True)
        content = load_fixture("md060", "aligned_delimiter.md")
        doc = Document(Path("aligned_delimiter.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_no_leading_pipe(self, rule: MD060) -> None:
        """Table without leading pipe character."""
        config = MD060Config(style="compact")
        content = load_fixture("md060", "no_leading_pipe.md")
        doc = Document(Path("no_leading_pipe.md"), content)

        violations = rule.check(doc, config)

        # Table without leading pipe should still be valid for compact style
        assert len(violations) == 0

    def test_misaligned_table(self, rule: MD060) -> None:
        """Misaligned table produces alignment violations."""
        config = MD060Config(style="aligned")
        content = load_fixture("md060", "misaligned.md")
        doc = Document(Path("misaligned.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 4
        assert violations[0].line == 5
        assert violations[0].column == 5
        assert violations[0].message == MD060.MSG_ALIGNED
        assert violations[2].line == 6
        assert violations[2].column == 6

    def test_aligned_delimiter_violation(self, rule: MD060) -> None:
        """Compact table with aligned_delimiter reports delimiter misalignment."""
        config = MD060Config(style="compact", aligned_delimiter=True)
        content = load_fixture("md060", "compact.md")
        doc = Document(Path("compact.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].line == 4
        assert violations[0].column == 7
        assert violations[0].message == MD060.MSG_ALIGNED_DELIMITER

    def test_any_style_selects_fewest(self, rule: MD060, config: MD060Config) -> None:
        """The 'any' style selects the style with fewest violations."""
        content = load_fixture("md060", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        # 'any' should pick compact (2 violations) over aligned (more) or tight (more)
        assert len(violations) == 2
        assert all("compact" in v.message for v in violations)

    def test_escaped_pipe(self, rule: MD060) -> None:
        """Escaped pipes are not treated as column separators."""
        config = MD060Config(style="compact")
        content = load_fixture("md060", "escaped_pipe.md")
        doc = Document(Path("escaped_pipe.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_empty_cells(self, rule: MD060) -> None:
        """Empty cells with single space are valid for compact style."""
        config = MD060Config(style="compact")
        content = load_fixture("md060", "empty_cells.md")
        doc = Document(Path("empty_cells.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_tables(self, rule: MD060) -> None:
        """Multiple tables in one document are checked independently."""
        config = MD060Config(style="compact")
        content = load_fixture("md060", "multiple_tables.md")
        doc = Document(Path("multiple_tables.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_cjk_aligned(self, rule: MD060) -> None:
        """CJK characters use visual width for alignment checking."""
        config = MD060Config(style="aligned")
        content = load_fixture("md060", "cjk_aligned.md")
        doc = Document(Path("cjk_aligned.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_any_style_valid_aligned(self, rule: MD060, config: MD060Config) -> None:
        """Any style accepts valid aligned table."""
        content = load_fixture("md060", "aligned.md")
        doc = Document(Path("aligned.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_any_style_valid_compact(self, rule: MD060, config: MD060Config) -> None:
        """Any style accepts valid compact table."""
        content = load_fixture("md060", "compact.md")
        doc = Document(Path("compact.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_any_style_valid_tight(self, rule: MD060, config: MD060Config) -> None:
        """Any style accepts valid tight table."""
        content = load_fixture("md060", "tight.md")
        doc = Document(Path("tight.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    @pytest.mark.parametrize("style", ["any", "compact"])
    def test_list_item_indentation_is_not_padding(
        self, rule: MD060, style: MD060Config.TableStyle
    ) -> None:
        """List item indentation before a row's first pipe is not cell padding."""
        config = MD060Config(style=style)
        content = load_fixture("md060", "list_item_compact.md")
        doc = Document(Path("list_item_compact.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_blockquote_marker_is_not_padding(self, rule: MD060) -> None:
        """The space after a blockquote marker is not cell padding."""
        config = MD060Config(style="tight")
        content = load_fixture("md060", "blockquote_tight.md")
        doc = Document(Path("blockquote_tight.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_containers_columns(self, rule: MD060) -> None:
        """Only unpadded rows are flagged, with columns that count the container prefix."""
        config = MD060Config(style="compact")
        content = load_fixture("md060", "containers.md")
        doc = Document(Path("containers.md"), content)

        violations = rule.check(doc, config)

        assert {v.line for v in violations} == {7, 11, 17}
        first = {v.line: v for v in reversed(violations)}
        assert first[7].column == 4
        assert first[11].column == 3
        assert first[17].column == 5
        assert all(v.message == MD060.MSG_COMPACT_MISSING_RIGHT for v in first.values())

    def test_block_start_first_cell_reported(self, rule: MD060) -> None:
        """Tables whose fix would start a list or heading are still reported."""
        config = MD060Config(style="compact")
        content = load_fixture("md060", "block_start_first_cell.md")
        doc = Document(Path("block_start_first_cell.md"), content)

        violations = rule.check(doc, config)

        assert {3, 9, 13} <= {v.line for v in violations}


class TestMD060Fix:
    @pytest.fixture
    def rule(self) -> MD060:
        return MD060()

    @pytest.fixture
    def config(self) -> MD060Config:
        return MD060Config()

    def test_fix_returns_none_for_valid(self, rule: MD060, config: MD060Config) -> None:
        """Fix returns None for already-valid content."""
        content = load_fixture("md060", "valid.md")
        doc = Document(Path("test.md"), content)
        assert rule.fix(doc, config) is None

    def test_fix_returns_none_for_no_table(self, rule: MD060, config: MD060Config) -> None:
        """Fix returns None when no tables exist."""
        content = load_fixture("md060", "no_table.md")
        doc = Document(Path("test.md"), content)
        assert rule.fix(doc, config) is None

    def test_fix_returns_none_for_valid_compact(self, rule: MD060) -> None:
        """Fix returns None for valid compact table."""
        config = MD060Config(style="compact")
        content = load_fixture("md060", "compact.md")
        doc = Document(Path("test.md"), content)
        assert rule.fix(doc, config) is None

    def test_fix_returns_none_for_valid_tight(self, rule: MD060) -> None:
        """Fix returns None for valid tight table."""
        config = MD060Config(style="tight")
        content = load_fixture("md060", "tight.md")
        doc = Document(Path("test.md"), content)
        assert rule.fix(doc, config) is None

    def test_fix_returns_none_for_valid_aligned(self, rule: MD060) -> None:
        """Fix returns None for valid aligned table."""
        config = MD060Config(style="aligned")
        content = load_fixture("md060", "aligned.md")
        doc = Document(Path("test.md"), content)
        assert rule.fix(doc, config) is None

    def test_fix_invalid_any_style(self, rule: MD060, config: MD060Config) -> None:
        """Fix corrects invalid table with 'any' style (picks compact)."""
        content = load_fixture("md060", "invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_compact_to_aligned(self, rule: MD060) -> None:
        """Fix reformats compact table to aligned style."""
        config = MD060Config(style="aligned")
        content = load_fixture("md060", "compact.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_tight_to_compact(self, rule: MD060) -> None:
        """Fix reformats tight table to compact style."""
        config = MD060Config(style="compact")
        content = load_fixture("md060", "tight.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_compact_to_tight(self, rule: MD060) -> None:
        """Fix reformats compact table to tight style."""
        config = MD060Config(style="tight")
        content = load_fixture("md060", "compact.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_misaligned_to_aligned(self, rule: MD060) -> None:
        """Fix corrects misaligned table to aligned style."""
        config = MD060Config(style="aligned")
        content = load_fixture("md060", "misaligned.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_compact_with_aligned_delimiter(self, rule: MD060) -> None:
        """Fix aligns delimiter row with header for aligned_delimiter option."""
        config = MD060Config(style="compact", aligned_delimiter=True)
        content = load_fixture("md060", "compact.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_returns_none_for_valid_aligned_delimiter(self, rule: MD060) -> None:
        """Fix returns None when aligned_delimiter is already satisfied."""
        config = MD060Config(style="compact", aligned_delimiter=True)
        content = load_fixture("md060", "aligned_delimiter.md")
        doc = Document(Path("test.md"), content)
        assert rule.fix(doc, config) is None

    def test_fix_preserves_escaped_pipes(self, rule: MD060) -> None:
        """Fix preserves escaped pipes within cells."""
        config = MD060Config(style="compact")
        content = load_fixture("md060", "escaped_pipe.md")
        doc = Document(Path("test.md"), content)
        assert rule.fix(doc, config) is None

    def test_fix_preserves_empty_cells(self, rule: MD060) -> None:
        """Fix preserves empty cells correctly."""
        config = MD060Config(style="compact")
        content = load_fixture("md060", "empty_cells.md")
        doc = Document(Path("test.md"), content)
        assert rule.fix(doc, config) is None

    def test_fix_multiple_tables(self, rule: MD060) -> None:
        """Fix returns None for valid multiple tables."""
        config = MD060Config(style="compact")
        content = load_fixture("md060", "multiple_tables.md")
        doc = Document(Path("test.md"), content)
        assert rule.fix(doc, config) is None

    def test_fix_cjk_aligned(self, rule: MD060) -> None:
        """Fix returns None for valid CJK aligned table."""
        config = MD060Config(style="aligned")
        content = load_fixture("md060", "cjk_aligned.md")
        doc = Document(Path("test.md"), content)
        assert rule.fix(doc, config) is None

    def test_fix_cjk_to_aligned(self, rule: MD060) -> None:
        """Fix reformats CJK compact table to aligned style."""
        config = MD060Config(style="aligned")
        content = """\
# CJK Table

| 名前 | 意味 |
| --- | --- |
| はい | Yes |
| いいえ | No |
"""
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_no_leading_pipe_compact(self, rule: MD060) -> None:
        """Fix returns None for valid table without leading pipes."""
        config = MD060Config(style="compact")
        content = load_fixture("md060", "no_leading_pipe.md")
        doc = Document(Path("test.md"), content)
        assert rule.fix(doc, config) is None

    def test_fix_no_leading_pipe_to_tight(self, rule: MD060) -> None:
        """Fix reformats table without leading pipes to tight style."""
        config = MD060Config(style="tight")
        content = load_fixture("md060", "no_leading_pipe.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    @pytest.mark.parametrize("style", ["any", "aligned", "compact", "tight"])
    def test_fix_single_dash_delimiter(self, rule: MD060, style: MD060Config.TableStyle) -> None:
        """A delimiter row without a leading pipe never becomes a list item."""
        config = MD060Config(style=style)
        content = load_fixture("md060", "single_dash_delimiter.md")
        result = _apply_fix(rule, content, config)
        assert result != content
        assert _table_cells(result) == _table_cells(content)
        assert _apply_fix(rule, result, config) == result
        if style != "any":
            assert rule.check(Document(Path("test.md"), result), config) == []

    def test_fix_single_dash_delimiter_compact_output(self, rule: MD060) -> None:
        """A lone dash first delimiter cell is widened instead of becoming a list marker."""
        config = MD060Config(style="compact")
        content = load_fixture("md060", "single_dash_delimiter.md")
        result = _apply_fix(rule, content, config)
        assert "Header |\n-- |\nText |\n" in result
        assert "a | b\n-- | -\nx | y\n" in result

    def test_fix_single_dash_delimiter_aligned_output(self, rule: MD060) -> None:
        """Aligned columns grow to fit the widened delimiter cell."""
        config = MD060Config(style="aligned")
        content = load_fixture("md060", "single_dash_delimiter.md")
        result = _apply_fix(rule, content, config)
        assert "a  | b\n-- | -\nx  | y\n" in result

    @pytest.mark.parametrize(
        ("style", "fixed_table"),
        [
            ("aligned", "a  | b\n-- | -\nx  | y\n"),
            ("compact", "a | b\n-- | -\nx | y\n"),
        ],
    )
    def test_fix_declines_block_start_first_cell(
        self, rule: MD060, style: MD060Config.TableStyle, fixed_table: str
    ) -> None:
        """Tables whose padded first cell would start a list or heading are left unchanged."""
        config = MD060Config(style=style)
        content = load_fixture("md060", "block_start_first_cell.md")
        result = _apply_fix(rule, content, config)
        head, tail = content.rsplit("a|b\n--|-\nx|y\n", 1)
        assert result == head + fixed_table + tail
        assert _table_cells(result) == _table_cells(content)
        assert _apply_fix(rule, result, config) == result

    def test_fix_containers_compact(self, rule: MD060) -> None:
        """Rows in list items and blockquotes keep their container prefix."""
        config = MD060Config(style="compact")
        content = load_fixture("md060", "containers.md")
        result = _apply_fix(rule, content, config)
        assert result == content.replace("|x|y|", "| x | y |")
        assert _table_cells(result) == _table_cells(content)
        assert _apply_fix(rule, result, config) == result
        assert rule.check(Document(Path("test.md"), result), config) == []

    def test_fix_containers_tight(self, rule: MD060) -> None:
        """Tight rows in containers keep the prefix and its trailing space."""
        config = MD060Config(style="tight")
        content = load_fixture("md060", "containers.md")
        result = _apply_fix(rule, content, config)
        assert result == content.replace("| a | b |", "|a|b|").replace("| - | - |", "|-|-|")
        assert _table_cells(result) == _table_cells(content)
        assert _apply_fix(rule, result, config) == result
        assert rule.check(Document(Path("test.md"), result), config) == []

    def test_fix_containers_aligned(self, rule: MD060) -> None:
        """Aligned fix measures columns after the container prefix."""
        config = MD060Config(style="aligned")
        content = load_fixture("md060", "containers.md")
        result = _apply_fix(rule, content, config)
        assert result == content.replace("|x|y|", "| x | y |")
        assert _table_cells(result) == _table_cells(content)
        assert _apply_fix(rule, result, config) == result
        assert rule.check(Document(Path("test.md"), result), config) == []
