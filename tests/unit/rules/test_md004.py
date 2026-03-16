from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md004 import MD004, MD004Config
from tests.conftest import load_fixture


class TestMD004:
    @pytest.fixture
    def rule(self) -> MD004:
        return MD004()

    @pytest.fixture
    def config(self) -> MD004Config:
        return MD004Config()

    def test_valid_consistent_markers(self, rule: MD004, config: MD004Config) -> None:
        """Valid document with consistent list markers."""
        content = load_fixture("md004", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_mixed_markers(self, rule: MD004, config: MD004Config) -> None:
        """Invalid document with mixed list markers."""
        content = load_fixture("md004", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].rule_id == "MD004"
        assert violations[0].line == 4
        assert "expected dash" in violations[0].message
        assert violations[1].line == 5
        assert "expected dash" in violations[1].message

    def test_no_lists(self, rule: MD004, config: MD004Config) -> None:
        """Document without lists."""
        content = load_fixture("md004", "no_lists.md")
        doc = Document(Path("no_lists.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_config_dash_style(self, rule: MD004) -> None:
        """Enforce dash style via config."""
        config = MD004Config(style="dash")
        content = load_fixture("md004", "dash.md")
        doc = Document(Path("dash.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_config_dash_style_violation(self, rule: MD004) -> None:
        """Dash style config with asterisk marker."""
        config = MD004Config(style="dash")
        content = load_fixture("md004", "asterisk.md")
        doc = Document(Path("asterisk.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 3
        assert "dash" in violations[0].message

    def test_single_item(self, rule: MD004, config: MD004Config) -> None:
        """Document with single list item."""
        content = load_fixture("md004", "single_item.md")
        doc = Document(Path("single.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_config_asterisk_style(self, rule: MD004) -> None:
        """Enforce asterisk style via config."""
        config = MD004Config(style="asterisk")
        content = load_fixture("md004", "asterisk.md")
        doc = Document(Path("asterisk.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_config_asterisk_style_violation(self, rule: MD004) -> None:
        """Asterisk style config with dash marker."""
        config = MD004Config(style="asterisk")
        content = load_fixture("md004", "dash.md")
        doc = Document(Path("dash.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 3
        assert "asterisk" in violations[0].message

    def test_config_plus_style(self, rule: MD004) -> None:
        """Enforce plus style via config."""
        config = MD004Config(style="plus")
        content = load_fixture("md004", "plus.md")
        doc = Document(Path("plus.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_config_plus_style_violation(self, rule: MD004) -> None:
        """Plus style config with dash marker."""
        config = MD004Config(style="plus")
        content = load_fixture("md004", "dash.md")
        doc = Document(Path("dash.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 3
        assert "plus" in violations[0].message

    def test_sublist_style_valid(self, rule: MD004) -> None:
        """Sublist mode with consistent markers per level."""
        config = MD004Config(style="sublist")
        content = load_fixture("md004", "sublist_valid.md")
        doc = Document(Path("sublist_valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_sublist_style_invalid(self, rule: MD004) -> None:
        """Sublist mode with inconsistent markers at same level."""
        config = MD004Config(style="sublist")
        content = load_fixture("md004", "sublist_invalid.md")
        doc = Document(Path("sublist_invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "level" in violations[0].message
        assert violations[0].line == 6

    def test_sublist_separate_lists_valid(self, rule: MD004) -> None:
        """Sublist mode with consistent markers per level across separate lists."""
        config = MD004Config(style="sublist")
        content = load_fixture("md004", "sublist_separate_valid.md")
        doc = Document(Path("sublist_separate_valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_sublist_separate_lists_invalid(self, rule: MD004) -> None:
        """Sublist mode detects inconsistent markers across separate lists."""
        config = MD004Config(style="sublist")
        content = load_fixture("md004", "sublist_separate_lists.md")
        doc = Document(Path("sublist_separate_lists.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 12
        assert "level" in violations[0].message

    def test_blockquote_consistent_list(self, rule: MD004, config: MD004Config) -> None:
        """Consistent list markers inside a blockquote."""
        content = load_fixture("md004", "blockquote_list.md")
        doc = Document(Path("blockquote_list.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_blockquote_mixed_list(self, rule: MD004, config: MD004Config) -> None:
        """Mixed list markers inside a blockquote."""
        content = load_fixture("md004", "blockquote_mixed.md")
        doc = Document(Path("blockquote_mixed.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].rule_id == "MD004"


class TestMD004Fix:
    @pytest.fixture
    def rule(self) -> MD004:
        return MD004()

    @pytest.fixture
    def config(self) -> MD004Config:
        return MD004Config()

    def test_fix_returns_none_for_valid(self, rule: MD004, config: MD004Config) -> None:
        """Valid document should return None (nothing to fix)."""
        content = load_fixture("md004", "valid.md")
        doc = Document(Path("test.md"), content)
        assert rule.fix(doc, config) is None

    def test_fix_returns_none_no_lists(self, rule: MD004, config: MD004Config) -> None:
        """Document with no lists should return None."""
        content = load_fixture("md004", "no_lists.md")
        doc = Document(Path("test.md"), content)
        assert rule.fix(doc, config) is None

    def test_fix_consistent_mixed_markers(self, rule: MD004, config: MD004Config) -> None:
        """Fix mixed markers in consistent mode (uses first marker as expected)."""
        content = load_fixture("md004", "invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []
        # First marker is dash, so all should become dashes
        assert "- Item with dash" in result
        assert "- Item with asterisk" in result
        assert "- Item with plus" in result

    def test_fix_to_asterisk_style(self, rule: MD004) -> None:
        """Fix dash markers to asterisk style."""
        config = MD004Config(style="asterisk")
        content = load_fixture("md004", "dash.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_to_plus_style(self, rule: MD004) -> None:
        """Fix dash markers to plus style."""
        config = MD004Config(style="plus")
        content = load_fixture("md004", "dash.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_to_dash_style(self, rule: MD004) -> None:
        """Fix asterisk markers to dash style."""
        config = MD004Config(style="dash")
        content = load_fixture("md004", "asterisk.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_returns_none_already_correct_style(self, rule: MD004) -> None:
        """Already correct style should return None."""
        config = MD004Config(style="dash")
        content = load_fixture("md004", "dash.md")
        doc = Document(Path("test.md"), content)
        assert rule.fix(doc, config) is None

    def test_fix_sublist_invalid(self, rule: MD004) -> None:
        """Fix sublist mode violations."""
        config = MD004Config(style="sublist")
        content = load_fixture("md004", "sublist_invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_sublist_returns_none_for_valid(self, rule: MD004) -> None:
        """Valid sublist document should return None."""
        config = MD004Config(style="sublist")
        content = load_fixture("md004", "sublist_valid.md")
        doc = Document(Path("test.md"), content)
        assert rule.fix(doc, config) is None

    def test_fix_sublist_separate_lists(self, rule: MD004) -> None:
        """Fix sublist violations across separate lists."""
        config = MD004Config(style="sublist")
        content = load_fixture("md004", "sublist_separate_lists.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_blockquote_mixed(self, rule: MD004, config: MD004Config) -> None:
        """Fix mixed markers inside a blockquote."""
        content = load_fixture("md004", "blockquote_mixed.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fixable_property(self, rule: MD004) -> None:
        """Rule should report as fixable."""
        assert rule.fixable is True
