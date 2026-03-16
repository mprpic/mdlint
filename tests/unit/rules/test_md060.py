from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md060 import MD060, MD060Config
from tests.conftest import load_fixture


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
