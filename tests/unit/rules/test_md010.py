from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md010 import MD010, MD010Config
from tests.conftest import load_fixture


class TestMD010:
    @pytest.fixture
    def rule(self) -> MD010:
        return MD010()

    @pytest.fixture
    def config(self) -> MD010Config:
        return MD010Config()

    def test_valid_document(self, rule: MD010, config: MD010Config) -> None:
        """Valid document with no hard tabs passes the rule."""
        content = load_fixture("md010", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD010, config: MD010Config) -> None:
        """Invalid document with hard tabs triggers violations."""
        content = load_fixture("md010", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].rule_id == "MD010"
        assert violations[0].rule_name == "no-hard-tabs"
        assert "tab" in violations[0].message.lower()

    def test_no_tabs(self, rule: MD010, config: MD010Config) -> None:
        """Document without any tabs."""
        content = load_fixture("md010", "no_tabs.md")
        doc = Document(Path("no_tabs.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_code_blocks_checked_by_default(self, rule: MD010, config: MD010Config) -> None:
        """Code blocks are checked for tabs by default."""
        content = load_fixture("md010", "code_block.md")
        doc = Document(Path("code_block.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].rule_id == "MD010"

    def test_code_blocks_ignored_when_configured(self, rule: MD010) -> None:
        """Code blocks are ignored when code_blocks=False."""
        config = MD010Config(code_blocks=False)
        content = load_fixture("md010", "code_block.md")
        doc = Document(Path("code_block.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_column_position_reported(self, rule: MD010, config: MD010Config) -> None:
        """Tab position is correctly reported as column number."""
        content = "Text\twith tab"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert violations[0].column == 5  # Tab starts at column 5

    def test_multiple_tabs_on_same_line(self, rule: MD010, config: MD010Config) -> None:
        """Multiple tabs on the same line are reported separately."""
        content = "\tFirst\tSecond"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].column == 1
        assert violations[1].column == 7

    def test_inline_code_checked_by_default(self, rule: MD010, config: MD010Config) -> None:
        """Inline code spans are checked for tabs by default."""
        content = load_fixture("md010", "inline_code.md")
        doc = Document(Path("inline_code.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2

    def test_inline_code_ignored_when_code_blocks_false(self, rule: MD010) -> None:
        """Inline code spans are ignored when code_blocks=False."""
        config = MD010Config(code_blocks=False)
        content = load_fixture("md010", "inline_code.md")
        doc = Document(Path("inline_code.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].column == 26  # Tab outside the code span

    def test_indented_code_block_ignored_when_configured(self, rule: MD010) -> None:
        """Indented code blocks are ignored when code_blocks=False."""
        config = MD010Config(code_blocks=False)
        content = load_fixture("md010", "indented_code_block.md")
        doc = Document(Path("indented_code_block.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_empty_document(self, rule: MD010, config: MD010Config) -> None:
        """Empty document has no violations."""
        content = ""
        doc = Document(Path("empty.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0


class TestMD010Fix:
    @pytest.fixture
    def rule(self) -> MD010:
        return MD010()

    @pytest.fixture
    def config(self) -> MD010Config:
        return MD010Config()

    def test_fix_corrects_invalid(self, rule: MD010, config: MD010Config) -> None:
        """Fix replaces hard tabs with spaces in invalid document."""
        content = load_fixture("md010", "invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_returns_none_for_valid(self, rule: MD010, config: MD010Config) -> None:
        """Fix returns None when there are no violations."""
        content = load_fixture("md010", "valid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_returns_none_for_no_tabs(self, rule: MD010, config: MD010Config) -> None:
        """Fix returns None for document without tabs."""
        content = load_fixture("md010", "no_tabs.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_replaces_tab_with_four_spaces(self, rule: MD010, config: MD010Config) -> None:
        """Fix replaces each tab with four spaces."""
        content = "Text\twith tab"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result == "Text    with tab"

    def test_fix_multiple_tabs_on_same_line(self, rule: MD010, config: MD010Config) -> None:
        """Fix replaces multiple tabs on the same line."""
        content = "\tFirst\tSecond"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result == "    First    Second"

    def test_fix_code_block_tabs_by_default(self, rule: MD010, config: MD010Config) -> None:
        """Fix replaces tabs in code blocks by default."""
        content = load_fixture("md010", "code_block.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_skips_code_blocks_when_configured(self, rule: MD010) -> None:
        """Fix skips code blocks when code_blocks=False."""
        config = MD010Config(code_blocks=False)
        content = load_fixture("md010", "code_block.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_inline_code_tabs_by_default(self, rule: MD010, config: MD010Config) -> None:
        """Fix replaces tabs in inline code spans by default."""
        content = load_fixture("md010", "inline_code.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_skips_inline_code_when_configured(self, rule: MD010) -> None:
        """Fix skips inline code tabs but fixes others when code_blocks=False."""
        config = MD010Config(code_blocks=False)
        content = load_fixture("md010", "inline_code.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        # Should still fix the tab outside the code span
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_empty_document(self, rule: MD010, config: MD010Config) -> None:
        """Fix returns None for empty document."""
        content = ""
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fixable_property(self, rule: MD010) -> None:
        """Rule reports as fixable."""
        assert rule.fixable is True
