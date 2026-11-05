from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md010 import MD010, MD010Config
from tests.conftest import load_fixture


def _fix_twice(rule: MD010, config: MD010Config, content: str) -> str:
    """Apply the fix and check that a second pass changes nothing."""
    result = rule.fix(Document(Path("test.md"), content), config)
    assert result is not None
    assert rule.fix(Document(Path("test.md"), result), config) is None
    return result


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

    def test_code_blocks_ignored_by_default(self, rule: MD010, config: MD010Config) -> None:
        """Code blocks are ignored by default."""
        content = load_fixture("md010", "code_block.md")
        doc = Document(Path("code_block.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_code_blocks_checked_when_configured(self, rule: MD010) -> None:
        """Code blocks are checked when code_blocks=True."""
        config = MD010Config(code_blocks=True)
        content = load_fixture("md010", "code_block.md")
        doc = Document(Path("code_block.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].rule_id == "MD010"

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
        content = "A\tFirst\tSecond"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].column == 2
        assert violations[1].column == 8

    def test_inline_code_checked_when_configured(self, rule: MD010) -> None:
        """Inline code spans are checked when code_blocks=True."""
        config = MD010Config(code_blocks=True)
        content = load_fixture("md010", "inline_code.md")
        doc = Document(Path("inline_code.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2

    def test_inline_code_ignored_by_default(self, rule: MD010, config: MD010Config) -> None:
        """Inline code spans are ignored by default."""
        content = load_fixture("md010", "inline_code.md")
        doc = Document(Path("inline_code.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].column == 26  # Tab outside the code span

    def test_indented_code_block_ignored_by_default(self, rule: MD010, config: MD010Config) -> None:
        """Indented code blocks are ignored by default."""
        content = load_fixture("md010", "indented_code_block.md")
        doc = Document(Path("indented_code_block.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_front_matter_ignored(self, rule: MD010) -> None:
        """Front matter is never checked, whatever code_blocks is set to."""
        content = load_fixture("md010", "front_matter.md")
        doc = Document(Path("front_matter.md"), content)

        assert rule.check(doc, MD010Config()) == []
        assert rule.check(doc, MD010Config(code_blocks=True)) == []

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

    def test_fix_expands_tab_to_next_tab_stop(self, rule: MD010, config: MD010Config) -> None:
        """A tab at column 4 reaches the next stop at column 8."""
        content = "Text\twith tab"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result == "Text    with tab"

    def test_fix_multiple_tabs_on_same_line(self, rule: MD010, config: MD010Config) -> None:
        """Each tab is padded to its own tab stop."""
        content = "A\tFirst\tSecond"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result == "A   First   Second"

    def test_fix_keeps_content_columns(self, rule: MD010, config: MD010Config) -> None:
        """Expanding to tab stops keeps list content and text on the same columns."""
        content = load_fixture("md010", "tab_stops.md")
        result = _fix_twice(rule, config, content)
        assert result == "# Tab Stops\n\n-   item\n    continuation\n\nAb  c   d\n"

    def test_fix_removes_trailing_tabs(self, rule: MD010, config: MD010Config) -> None:
        """Trailing whitespace containing a tab is removed rather than becoming a hard break."""
        content = load_fixture("md010", "trailing_tabs.md")
        result = _fix_twice(rule, config, content)
        assert result == "# Trailing Tabs\n\ntext\nnext line\n\nmixed\nend\n"

    def test_fix_keeps_hard_break_after_tab(self, rule: MD010, config: MD010Config) -> None:
        """Two or more spaces after a trailing tab are a hard break, and the fix keeps them."""
        content = load_fixture("md010", "trailing_tab_hard_break.md")
        result = _fix_twice(rule, config, content)
        assert result == "# Hard Break\n\nbreak  \nnext line\n\nno break\nend\n"

    def test_fix_skips_front_matter(self, rule: MD010, config: MD010Config) -> None:
        """Fix never rewrites front matter."""
        content = load_fixture("md010", "front_matter.md")
        doc = Document(Path("test.md"), content)
        assert rule.fix(doc, config) is None

    def test_fix_code_block_tabs_when_configured(self, rule: MD010) -> None:
        """Fix replaces tabs in code blocks when code_blocks=True."""
        config = MD010Config(code_blocks=True)
        content = load_fixture("md010", "code_block.md")
        result = _fix_twice(rule, config, content)
        assert '    return "world"' in result

    def test_fix_skips_code_blocks_by_default(self, rule: MD010, config: MD010Config) -> None:
        """Fix leaves code blocks alone by default."""
        content = load_fixture("md010", "code_block.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_inline_code_tabs_when_configured(self, rule: MD010) -> None:
        """Fix replaces tabs in inline code spans when code_blocks=True."""
        config = MD010Config(code_blocks=True)
        content = load_fixture("md010", "inline_code.md")
        result = _fix_twice(rule, config, content)
        assert result == "# Inline code with tabs\n\nSome `code  here` and text  with tab.\n"

    def test_fix_skips_inline_code_by_default(self, rule: MD010, config: MD010Config) -> None:
        """Fix keeps the code span tab and pads the later tab to the original tab stop."""
        content = load_fixture("md010", "inline_code.md")
        result = _fix_twice(rule, config, content)
        assert result == "# Inline code with tabs\n\nSome `code\there` and text  with tab.\n"

    def test_fix_empty_document(self, rule: MD010, config: MD010Config) -> None:
        """Fix returns None for empty document."""
        content = ""
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fixable_property(self, rule: MD010) -> None:
        """Rule reports as fixable."""
        assert rule.fixable is True
