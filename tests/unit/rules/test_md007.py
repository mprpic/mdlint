from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md007 import MD007, MD007Config
from tests.conftest import load_fixture


class TestMD007:
    @pytest.fixture
    def rule(self) -> MD007:
        return MD007()

    @pytest.fixture
    def config(self) -> MD007Config:
        return MD007Config()

    def test_valid_document(self, rule: MD007, config: MD007Config) -> None:
        """Valid document with correct 2-space indentation."""
        content = load_fixture("md007", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD007, config: MD007Config) -> None:
        """Invalid document with incorrect indentation."""
        content = load_fixture("md007", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].rule_id == "MD007"
        assert violations[0].line == 4
        assert "Expected 2 spaces, found 3" in violations[0].message
        assert violations[1].line == 6
        assert "Expected 2 spaces, found 4" in violations[1].message

    def test_custom_indent(self, rule: MD007) -> None:
        """Test with custom 4-space indentation."""
        content = load_fixture("md007", "indent_4.md")
        doc = Document(Path("indent_4.md"), content)
        config = MD007Config(indent=4)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_start_indented(self, rule: MD007) -> None:
        """Test with start_indented enabled."""
        content = load_fixture("md007", "start_indented.md")
        doc = Document(Path("start_indented.md"), content)
        config = MD007Config(start_indented=True, start_indent=2)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_mixed_list_types(self, rule: MD007, config: MD007Config) -> None:
        """Test that rule only applies to unordered sublists under unordered parents."""
        content = load_fixture("md007", "mixed_list.md")
        doc = Document(Path("mixed_list.md"), content)

        violations = rule.check(doc, config)

        # Rule should not flag unordered lists under ordered lists
        assert len(violations) == 0

    def test_no_lists(self, rule: MD007, config: MD007Config) -> None:
        """Document without lists."""
        content = load_fixture("md007", "no_lists.md")
        doc = Document(Path("no_lists.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_start_indented_violations(self, rule: MD007) -> None:
        """Non-indented top-level items should be flagged when start_indented is True."""
        content = load_fixture("md007", "start_indented_invalid.md")
        doc = Document(Path("start_indented_invalid.md"), content)
        config = MD007Config(start_indented=True)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].line == 3
        assert "Expected 2 spaces, found 0" in violations[0].message
        assert violations[1].line == 4
        assert "Expected 2 spaces, found 0" in violations[1].message

    def test_custom_start_indent(self, rule: MD007) -> None:
        """Test start_indented with explicit start_indent different from indent."""
        content = load_fixture("md007", "start_indent_custom.md")
        doc = Document(Path("start_indent_custom.md"), content)
        config = MD007Config(indent=2, start_indented=True, start_indent=2)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_start_indent_defaults_to_indent(self, rule: MD007) -> None:
        """When start_indent is not set, it defaults to the indent value."""
        content = load_fixture("md007", "indent_4.md")
        doc = Document(Path("indent_4.md"), content)
        config = MD007Config(indent=4, start_indented=True)

        violations = rule.check(doc, config)

        # indent_4.md has top-level items at 0 indent, but start_indented expects 4
        assert len(violations) > 0
        assert "Expected 4 spaces, found 0" in violations[0].message

    def test_blockquote_list(self, rule: MD007, config: MD007Config) -> None:
        """Lists inside blockquotes should not produce false positives."""
        content = load_fixture("md007", "blockquote.md")
        doc = Document(Path("blockquote.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_blockquote_in_list(self, rule: MD007, config: MD007Config) -> None:
        """A list inside a blockquote starts a new nesting level at the blockquote."""
        content = load_fixture("md007", "blockquote_in_list.md")
        doc = Document(Path("blockquote_in_list.md"), content)

        violations = rule.check(doc, config)

        assert violations == []

    def test_blockquote_with_ordered_parent(self, rule: MD007, config: MD007Config) -> None:
        """An ordered list outside the blockquote does not exempt the bullets inside it."""
        content = load_fixture("md007", "blockquote_ordered_parent.md")
        doc = Document(Path("blockquote_ordered_parent.md"), content)

        violations = rule.check(doc, config)

        assert [v.line for v in violations] == [5]
        assert "Expected 2 spaces, found 3" in violations[0].message

    def test_continuation_lines(self, rule: MD007, config: MD007Config) -> None:
        """Only the nested item's marker line is reported."""
        content = load_fixture("md007", "continuation_lines.md")
        doc = Document(Path("continuation_lines.md"), content)

        violations = rule.check(doc, config)

        assert [v.line for v in violations] == [4]
        assert "Expected 2 spaces, found 4" in violations[0].message

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = MD007Config()

        assert config.indent == 2
        assert config.start_indented is False
        # start_indent defaults to indent value via __post_init__
        assert config.start_indent == 2

    def test_start_indent_inherits_custom_indent(self) -> None:
        """start_indent should default to indent when not explicitly set."""
        config = MD007Config(indent=4)

        assert config.start_indent == 4

    def test_fix_corrects_invalid(self, rule: MD007, config: MD007Config) -> None:
        """Fix should correct indentation violations."""
        content = load_fixture("md007", "invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_returns_none_for_valid(self, rule: MD007, config: MD007Config) -> None:
        """Valid document should return None (nothing to fix)."""
        content = load_fixture("md007", "valid.md")
        doc = Document(Path("test.md"), content)
        assert rule.fix(doc, config) is None

    def test_fix_returns_none_no_lists(self, rule: MD007, config: MD007Config) -> None:
        """Document without lists should return None."""
        content = load_fixture("md007", "no_lists.md")
        doc = Document(Path("test.md"), content)
        assert rule.fix(doc, config) is None

    def test_fix_start_indented(self, rule: MD007) -> None:
        """Fix should add indentation when start_indented is True."""
        content = load_fixture("md007", "start_indented_invalid.md")
        doc = Document(Path("test.md"), content)
        config = MD007Config(start_indented=True)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_keeps_siblings_of_an_item_it_cannot_move(self, rule: MD007) -> None:
        """If one item of a list cannot move, its siblings stay put too, keeping the nesting."""
        content = load_fixture("md007", "declined_sibling.md")
        doc = Document(Path("test.md"), content)
        config = MD007Config(start_indented=True)

        assert rule.check(doc, config) != []
        assert rule.fix(doc, config) is None

    def test_fix_blockquote_returns_none(self, rule: MD007, config: MD007Config) -> None:
        """Valid blockquote list should return None."""
        content = load_fixture("md007", "blockquote.md")
        doc = Document(Path("test.md"), content)
        assert rule.fix(doc, config) is None

    def test_fix_mixed_list_returns_none(self, rule: MD007, config: MD007Config) -> None:
        """Mixed list types (no violations) should return None."""
        content = load_fixture("md007", "mixed_list.md")
        doc = Document(Path("test.md"), content)
        assert rule.fix(doc, config) is None

    def test_fixable_property(self, rule: MD007) -> None:
        """Rule should report as fixable."""
        assert rule.fixable is True

    def test_fix_blockquote_with_ordered_parent(self, rule: MD007, config: MD007Config) -> None:
        """Fix re-indents the nested bullet inside the blockquote."""
        content = load_fixture("md007", "blockquote_ordered_parent.md")
        result = rule.fix(Document(Path("test.md"), content), config)
        assert result == (
            "# Ordered Ancestor Outside Blockquote\n\n1. Item\n   > - Quoted item\n"
            "   >   - Nested with 3 spaces\n"
        )
        assert rule.check(Document(Path("test.md"), result), config) == []

    def test_fix_shifts_continuation_lines(self, rule: MD007, config: MD007Config) -> None:
        """Fix moves the whole item, including fenced code inside it."""
        content = load_fixture("md007", "continuation_lines.md")
        result = rule.fix(Document(Path("test.md"), content), config)
        assert result == (
            "# Continuation Lines\n\n- Item\n  - Nested item\n    continuation of nested item\n"
            "\n    ```text\n    code in nested item\n    ```\n"
        )
        fixed = Document(Path("test.md"), result)
        assert rule.check(fixed, config) == []
        fence = next(token for token in fixed.tokens if token.type == "fence")
        assert fence.content == "code in nested item\n"

    def test_fix_declines_when_item_would_leave_parent(
        self, rule: MD007, config: MD007Config
    ) -> None:
        """Items that cannot move without changing the list structure are only reported."""
        content = load_fixture("md007", "fix_declines.md")
        doc = Document(Path("test.md"), content)

        assert [v.line for v in rule.check(doc, config)] == [4, 9]
        assert rule.fix(doc, config) is None

    @pytest.mark.parametrize(
        "filename", ["invalid.md", "blockquote_ordered_parent.md", "continuation_lines.md"]
    )
    def test_fix_is_idempotent(self, rule: MD007, config: MD007Config, filename: str) -> None:
        """Fixing an already fixed document changes nothing."""
        content = load_fixture("md007", filename)
        once = rule.fix(Document(Path("test.md"), content), config)
        assert once is not None
        assert rule.fix(Document(Path("test.md"), once), config) is None
